# Database Layer

PostgreSQL database schema and ORM models for policy storage.

## Overview

SQLAlchemy-based database layer storing policy documents, chunks, and metadata.

## Schema

```
policy_sources (documents)
    ↓ 1:N
policy_chunks (text segments)
```

## Tables

### policy_sources

Stores raw policy documents and metadata.

**Columns:**

- `doc_id` (String, Primary Key): Unique document identifier
- `url` (String): Source URL
- `html_content` (Text): Raw HTML
- `policy_source` (String): Policy name (e.g., "Google Ads Policy")
- `region` (String): Geographic scope (e.g., "Global")
- `content_type` (String): Document type (e.g., "Advertising Policy")
- `download_date` (DateTime): When document was fetched
- `metadata_json` (JSON): Additional structured data

**Example row:**

```python
{
    "doc_id": "google_ads_overview",
    "url": "https://support.google.com/adspolicy/answer/6008942",
    "html_content": "<html>...</html>",
    "policy_source": "Google Ads Policy",
    "region": "Global",
    "content_type": "Advertising Policy",
    "download_date": "2025-12-24 10:30:00",
    "metadata_json": {
        "section_urls": {
            "Alcohol": "https://support.google.com/adspolicy/answer/6012382",
            "Gambling": "https://support.google.com/adspolicy/answer/6018017"
        }
    }
}
```

### policy_chunks

Stores processed text chunks with hierarchical metadata.

**Columns:**

- `chunk_id` (String, Primary Key): Unique chunk identifier
- `doc_id` (String, Foreign Key → policy_sources): Parent document
- `chunk_text` (Text): Actual content
- `policy_section` (String): Section name (e.g., "Alcohol")
- `policy_path` (String): Full hierarchy (e.g., "Prohibited Content > Alcohol")
- `policy_section_level` (String): HTML level (h1, h2, h3, h4)
- `chunk_index` (Integer): Position in document
- `doc_url` (String): Section-specific policy URL
- `created_at` (DateTime): When chunk was created

**Example row:**

```python
{
    "chunk_id": "google_ads_overview_chunk_005",
    "doc_id": "google_ads_overview",
    "chunk_text": "Alcohol advertising requires certification...",
    "policy_section": "Alcohol",
    "policy_path": "Prohibited Content > Alcohol",
    "policy_section_level": "h2",
    "chunk_index": 5,
    "doc_url": "https://support.google.com/adspolicy/answer/6012382",
    "created_at": "2025-12-24 10:31:00"
}
```

## Models

### PolicySource (db/models.py)

```python
class PolicySource(Base):
    __tablename__ = "policy_sources"

    doc_id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    html_content = Column(Text, nullable=False)
    policy_source = Column(String, nullable=False)
    region = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    download_date = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON)

    # Relationship
    chunks = relationship("PolicyChunk", back_populates="source")
```

### PolicyChunk (db/models.py)

```python
class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    chunk_id = Column(String, primary_key=True)
    doc_id = Column(String, ForeignKey("policy_sources.doc_id"))
    chunk_text = Column(Text, nullable=False)
    policy_section = Column(String, nullable=False)
    policy_path = Column(String, nullable=False)
    policy_section_level = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    doc_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    source = relationship("PolicySource", back_populates="chunks")
```

## Session Management

### SessionLocal (db/session.py)

```python
from db.session import SessionLocal

# Create session
db = SessionLocal()

try:
    # Query database
    chunks = db.query(PolicyChunk).filter_by(doc_id="google_ads_overview").all()

    # Insert data
    chunk = PolicyChunk(
        chunk_id="new_chunk_001",
        doc_id="google_ads_overview",
        chunk_text="New content...",
        # ...
    )
    db.add(chunk)
    db.commit()

finally:
    db.close()
```

### Dependency Injection (db/session.py)

```python
from db.session import get_db

def some_function(db: Session = Depends(get_db)):
    # db automatically managed
    chunks = db.query(PolicyChunk).all()
    # Session auto-closed after function
```

## Database Initialization

```python
from db.session import init_db

# Create all tables
init_db()
```

**SQL equivalent:**

```sql
CREATE TABLE policy_sources (
    doc_id VARCHAR PRIMARY KEY,
    url VARCHAR NOT NULL,
    html_content TEXT NOT NULL,
    policy_source VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata_json JSON
);

CREATE TABLE policy_chunks (
    chunk_id VARCHAR PRIMARY KEY,
    doc_id VARCHAR REFERENCES policy_sources(doc_id),
    chunk_text TEXT NOT NULL,
    policy_section VARCHAR NOT NULL,
    policy_path VARCHAR NOT NULL,
    policy_section_level VARCHAR NOT NULL,
    chunk_index INTEGER NOT NULL,
    doc_url VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chunks_doc_id ON policy_chunks(doc_id);
CREATE INDEX idx_chunks_section ON policy_chunks(policy_section);
```

## Queries

### Common Queries

**Get all chunks for a document:**

```python
from db.session import SessionLocal
from db.models import PolicyChunk

db = SessionLocal()
chunks = db.query(PolicyChunk).filter_by(doc_id="google_ads_overview").all()

for chunk in chunks:
    print(f"{chunk.policy_section}: {chunk.chunk_text[:50]}")
```

**Get chunks by section:**

```python
alcohol_chunks = db.query(PolicyChunk).filter_by(
    policy_section="Alcohol"
).all()
```

**Count chunks per document:**

```python
from sqlalchemy import func

counts = db.query(
    PolicyChunk.doc_id,
    func.count(PolicyChunk.chunk_id).label("count")
).group_by(PolicyChunk.doc_id).all()

for doc_id, count in counts:
    print(f"{doc_id}: {count} chunks")
```

**Get document with chunks:**

```python
from db.models import PolicySource

source = db.query(PolicySource).filter_by(
    doc_id="google_ads_overview"
).first()

print(f"Document: {source.policy_source}")
print(f"Chunks: {len(source.chunks)}")

for chunk in source.chunks:
    print(f"  - {chunk.policy_section}")
```

### SQL Queries

**Direct SQL execution:**

```python
from db.session import engine

with engine.connect() as conn:
    result = conn.execute("SELECT COUNT(*) FROM policy_chunks")
    count = result.scalar()
    print(f"Total chunks: {count}")
```

**Using psql:**

```bash
# Connect to database
psql ads_policy_rag

# List tables
\dt

# Count chunks
SELECT COUNT(*) FROM policy_chunks;

# View chunk distribution
SELECT policy_section, COUNT(*) as count
FROM policy_chunks
GROUP BY policy_section
ORDER BY count DESC;

# Sample chunks
SELECT chunk_id, policy_section, LEFT(chunk_text, 50) as preview
FROM policy_chunks
LIMIT 10;
```

## Configuration

**Environment variables:**

```bash
# PostgreSQL connection
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ads_policy_rag
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Or full connection string
DATABASE_URL=postgresql://user:pass@localhost:5432/ads_policy_rag
```

**Connection string format:**

```python
# In db/session.py
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{user}:{password}@{host}:{port}/{database}"
)
```

## Maintenance

### Backup

```bash
# Dump database
pg_dump ads_policy_rag > backup.sql

# Dump specific table
pg_dump ads_policy_rag -t policy_chunks > chunks_backup.sql

# Dump schema only
pg_dump ads_policy_rag --schema-only > schema.sql
```

### Restore

```bash
# Restore full database
psql ads_policy_rag < backup.sql

# Restore specific table
psql ads_policy_rag < chunks_backup.sql
```

### Clear Data

```python
from db.session import SessionLocal
from db.models import PolicyChunk, PolicySource

db = SessionLocal()

# Delete all chunks
db.query(PolicyChunk).delete()
db.commit()

# Delete all sources (cascades to chunks)
db.query(PolicySource).delete()
db.commit()
```

**SQL:**

```sql
-- Delete all data
DELETE FROM policy_chunks;
DELETE FROM policy_sources;

-- Reset sequences (if using auto-increment)
-- Not applicable here (using string PKs)
```

### Rebuild Database

```bash
# Drop and recreate
psql postgres -c "DROP DATABASE IF EXISTS ads_policy_rag;"
psql postgres -c "CREATE DATABASE ads_policy_rag;"

# Initialize tables
python -c "from db.session import init_db; init_db()"

# Re-run ingestion pipeline
python -m ingestion.load_docs
python -m ingestion.chunk
python -m ingestion.embed
```

## Indexes

**Automatic indexes:**

- Primary keys (`doc_id`, `chunk_id`)
- Foreign keys (`chunks.doc_id`)

**Additional indexes (optional):**

```sql
-- Speed up section filtering
CREATE INDEX idx_chunks_section ON policy_chunks(policy_section);

-- Speed up region filtering
CREATE INDEX idx_sources_region ON policy_sources(region);

-- Speed up content type filtering
CREATE INDEX idx_sources_content_type ON policy_sources(content_type);

-- Composite index for common filters
CREATE INDEX idx_chunks_doc_section ON policy_chunks(doc_id, policy_section);
```

## Performance

**Current scale:**

- ~5-10 documents
- ~67 chunks
- Query time: <10ms

**Expected scale:**

- 100s of documents: Fast
- 1000s of chunks: Fast
- 10,000s of chunks: Add indexes

**Optimization tips:**

- Use connection pooling (SQLAlchemy default)
- Add indexes for frequently filtered columns
- Use `db.query().limit()` for pagination
- Avoid loading full `html_content` unless needed

## Testing

```bash
# Test database connection
python -c "from db.session import engine; engine.connect(); print('Connected')"

# Test table creation
python -c "from db.session import init_db; init_db(); print('Tables created')"

# Test data insertion
python -c "
from db.session import SessionLocal
from db.models import PolicyChunk
from datetime import datetime

db = SessionLocal()
chunk = PolicyChunk(
    chunk_id='test_001',
    doc_id='test_doc',
    chunk_text='Test content',
    policy_section='Test',
    policy_path='Test',
    policy_section_level='h1',
    chunk_index=1,
    doc_url='http://example.com'
)
db.add(chunk)
db.commit()
print('Chunk inserted')
db.close()
"
```

## Migrations

Currently using direct table creation (`init_db()`). For production, consider migrations:

**Alembic setup:**

```bash
# Install
pip install alembic

# Initialize
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## Docker

**Database in Docker Compose:**

```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: policy_rag
    POSTGRES_USER: policy_user
    POSTGRES_PASSWORD: policy_pass
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

**Connect from container:**

```python
# Host is service name in Docker network
DATABASE_URL = "postgresql://policy_user:policy_pass@postgres:5432/policy_rag"
```

## Architecture Decisions

**Why PostgreSQL?**

- Reliable and mature
- JSON support for metadata
- Good performance at scale
- Easy to backup/restore
- Industry standard

**Why SQLAlchemy ORM?**

- Pythonic database access
- Type safety
- Relationship management
- Easy testing (can mock)
- Database-agnostic (can switch DB)

**Why string primary keys?**

- Meaningful identifiers
- No auto-increment complexity
- Easy to debug
- Human-readable in logs

**Why separate chunks table?**

- Enables chunk-level metadata
- Efficient retrieval queries
- Clear data model
- Supports vector index rebuilds

**Why store HTML?**

- Enables re-chunking without re-download
- Preserves source data
- Debugging and auditing
- Can extract new fields later
