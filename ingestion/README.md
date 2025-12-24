# Ingestion Pipeline

Data ingestion and preprocessing pipeline for policy documents.

## Overview

The ingestion pipeline downloads, chunks, and embeds Google Ads policy documents for semantic search. It consists of three stages that run sequentially.

## Pipeline Stages

```
load_docs.py → chunk.py → embed.py
     ↓            ↓          ↓
  metadata    chunks     Weaviate
   .json       .json    (vectors)
     +           +          +
PostgreSQL  PostgreSQL  PostgreSQL
```

## Components

### 1. Document Loader (`load_docs.py`)

Downloads policy documents from Google Ads Policy Center and extracts metadata.

**What it does:**

- Scrapes HTML from Google Ads policy URLs
- Extracts section-specific URLs from document structure
- Parses metadata (region, content type, policy source)
- Saves to `data/metadata.json`
- Stores in PostgreSQL `policy_sources` table

**Key features:**

- **Automated URL extraction**: Finds section-specific policy URLs in HTML
- **No hardcoding**: URLs discovered dynamically from document structure
- **Multiple policy sources**: Global, regional, content-specific
- **Idempotent**: Safe to re-run

**Usage:**

```bash
# Download all policy documents
python -m ingestion.load_docs

# Output: data/metadata.json
# Structure:
{
  "doc_id": "google_ads_overview",
  "url": "https://support.google.com/adspolicy/...",
  "html_content": "...",
  "section_urls": {
    "Alcohol": "https://support.google.com/adspolicy/answer/6012382",
    "Gambling": "https://support.google.com/adspolicy/answer/6018017"
  },
  "policy_source": "Google Ads Policy",
  "region": "Global",
  "content_type": "Advertising Policy"
}
```

**Configuration:**

- URLs defined in `POLICY_URLS` list at top of file
- Easily extensible for new policy sources

**Error handling:**

- Retries on HTTP failures
- Validates HTML structure
- Logs warnings for missing sections

### 2. Document Chunker (`chunk.py`)

Splits documents into semantic chunks and assigns section-specific URLs.

**What it does:**

- Loads documents from `data/metadata.json`
- Parses HTML to identify sections (h1, h2, h3, h4)
- Creates hierarchical chunks preserving structure
- Assigns section-specific URLs dynamically
- Saves to `data/chunks.json`
- Stores in PostgreSQL `policy_chunks` table

**Chunking strategy:**

- **Section-based**: Each policy section becomes a chunk
- **Hierarchical**: Preserves h1 → h2 → h3 → h4 structure
- **Contextual**: Includes section path (e.g., "Prohibited Content > Alcohol")
- **Size-aware**: ~500 token average per chunk

**URL assignment:**

- Exact match: "Alcohol" → metadata['section_urls']['Alcohol']
- Partial match: "Alcohol Products" → finds "Alcohol"
- Fallback: Uses document URL if no section match

**Usage:**

```bash
# Chunk all documents
python -m ingestion.chunk

# Output: data/chunks.json
# Structure:
{
  "chunk_id": "google_ads_overview_chunk_001",
  "doc_id": "google_ads_overview",
  "section_name": "Alcohol",
  "section_level": "h2",
  "chunk_text": "Alcohol advertising requires...",
  "policy_path": "Prohibited Content > Alcohol",
  "doc_url": "https://support.google.com/adspolicy/answer/6012382"
}
```

**Functions:**

- `extract_sections(html)`: Parses HTML into section hierarchy
- `create_chunks(sections, metadata)`: Generates chunks with URLs
- `get_policy_url(section_name, metadata)`: Dynamic URL lookup

### 3. Embedder (`embed.py`)

Generates embeddings and indexes chunks in Weaviate vector database.

**What it does:**

- Loads chunks from PostgreSQL
- Generates embeddings using sentence-transformers
- Creates Weaviate schema if needed
- Batch uploads chunks with vectors
- Enables semantic search

**Embedding model:**

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Performance**: Fast inference, good quality
- **Size**: 80MB download

**Weaviate schema:**

```python
{
  "class": "PolicyChunk",
  "properties": [
    {"name": "chunk_id", "dataType": ["text"]},
    {"name": "chunk_text", "dataType": ["text"]},
    {"name": "policy_section", "dataType": ["text"]},
    {"name": "policy_path", "dataType": ["text"]},
    {"name": "doc_id", "dataType": ["text"]},
    {"name": "doc_url", "dataType": ["text"]},
    {"name": "policy_source", "dataType": ["text"]},
    {"name": "region", "dataType": ["text"]},
    {"name": "content_type", "dataType": ["text"]}
  ]
}
```

**Usage:**

```bash
# Generate embeddings and index
python -m ingestion.embed

# Check indexed count
curl http://localhost:8080/v1/objects?class=PolicyChunk&limit=1
```

**Performance:**

- ~67 chunks indexed
- ~5 seconds total (including model load)
- Batch size: 100 chunks

## Running the Pipeline

**Full pipeline:**

```bash
# Run all three stages
python -m ingestion.load_docs
python -m ingestion.chunk
python -m ingestion.embed

# Or in one command
python -m ingestion.load_docs && \
python -m ingestion.chunk && \
python -m ingestion.embed
```

**Prerequisites:**

- PostgreSQL running (localhost:5432)
- Weaviate running (localhost:8080)
- Database tables created (`python -c "from db.session import init_db; init_db()"`)

**Docker (automated):**

```bash
# Pipeline runs automatically on container startup
docker-compose up -d

# Startup script checks and runs each stage if needed
```

## Data Flow

1. **Input**: Policy URLs (hardcoded in `load_docs.py`)
2. **Stage 1**: Download HTML → `data/metadata.json` + PostgreSQL
3. **Stage 2**: Parse & chunk → `data/chunks.json` + PostgreSQL
4. **Stage 3**: Embed & index → Weaviate vectors + PostgreSQL
5. **Output**: Searchable vector index + structured metadata

## File Outputs

```
data/
├── metadata.json       # Raw documents with section URLs
└── chunks.json         # Processed chunks with metadata
```

## Database Tables

**policy_sources:**

- Stores raw document metadata
- Primary key: `doc_id`

**policy_chunks:**

- Stores processed chunks
- Primary key: `chunk_id`
- Foreign key: `doc_id` → `policy_sources`

## Configuration

**Environment variables:**

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=policy_rag
POSTGRES_USER=policy_user
POSTGRES_PASSWORD=policy_pass

# Weaviate
WEAVIATE_URL=http://localhost:8080
```

## Adding New Policy Sources

1. Add URL to `POLICY_URLS` in `load_docs.py`
2. Run pipeline:
   ```bash
   python -m ingestion.load_docs
   python -m ingestion.chunk
   python -m ingestion.embed
   ```

Example:

```python
POLICY_URLS = [
    "https://support.google.com/adspolicy/answer/6008942",
    "https://your-new-policy-url.com",  # Add here
]
```

## Troubleshooting

**Issue: No chunks generated**

```bash
# Check metadata file exists
ls -lh data/metadata.json

# Check content
head data/metadata.json
```

**Issue: Weaviate connection failed**

```bash
# Check Weaviate is running
curl http://localhost:8080/v1/.well-known/ready

# Start Weaviate
docker-compose up -d weaviate
```

**Issue: Embeddings not indexed**

```bash
# Check Weaviate schema
curl http://localhost:8080/v1/schema

# Delete and recreate
curl -X DELETE http://localhost:8080/v1/schema/PolicyChunk
python -m ingestion.embed
```

**Issue: Duplicate chunks**

```bash
# Clear PostgreSQL
psql ads_policy_rag -c "DELETE FROM policy_chunks;"
psql ads_policy_rag -c "DELETE FROM policy_sources;"

# Clear Weaviate
curl -X DELETE http://localhost:8080/v1/schema/PolicyChunk

# Re-run pipeline
python -m ingestion.load_docs
python -m ingestion.chunk
python -m ingestion.embed
```

## Testing

```bash
# Test document loading
python -c "from ingestion.load_docs import download_policy; download_policy('https://support.google.com/adspolicy/answer/6008942')"

# Test chunking
python -c "from ingestion.chunk import extract_sections; import json; sections = extract_sections(json.load(open('data/metadata.json'))[0]['html_content']); print(len(sections))"

# Test embedding
python -c "from ingestion.embed import get_weaviate_client; client = get_weaviate_client(); print(client.schema.get())"
```

## Performance

**Benchmarks (67 chunks):**

- Document download: ~2 seconds
- Chunking: ~1 second
- Embedding: ~5 seconds
- **Total**: ~8 seconds

**Scaling:**

- 1000 chunks: ~45 seconds
- 10000 chunks: ~7 minutes
- Bottleneck: Embedding model inference

**Optimization tips:**

- Use GPU for embedding (2-3x faster)
- Increase batch size for large datasets
- Cache embeddings between runs
- Use faster embedding model (trade-off: quality)

## Architecture Decisions

**Why section-specific URLs?**

- Better user experience (direct links to policy)
- More accurate citations
- Scalable (no hardcoded mappings)

**Why sentence-transformers?**

- Best quality/speed trade-off
- Local inference (no API costs)
- Production-ready

**Why Weaviate?**

- Fast vector search
- Hybrid search support (semantic + keyword)
- Production scalability
- Open source

**Why three-stage pipeline?**

- Modularity (can re-run stages independently)
- Debugging (inspect intermediate outputs)
- Flexibility (swap components easily)
