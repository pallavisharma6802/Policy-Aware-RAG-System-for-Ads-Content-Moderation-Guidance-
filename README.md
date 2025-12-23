# Policy-Aware RAG System for Ads & Content Moderation Guidance

A customer-facing Retrieval-Augmented Generation (RAG) system that provides policy explanation and guidance for Google Ads content moderation. The system uses hybrid retrieval (semantic + SQL) to find relevant policy sections and generates grounded, citation-backed explanations.

## Core Features

- Hybrid retrieval: Vector similarity search (Weaviate) + SQL metadata filtering (PostgreSQL)
- Grounded generation: LLM responses cite source policies
- Refusal handling: System explicitly refuses when no policy applies
- Structured filtering: Filter by region, content type, policy section

## Technology Stack

### Data & Storage

- PostgreSQL: Structured metadata (region, content type, policy source)
- Weaviate: Vector database for semantic search
- SQLAlchemy: ORM for database interactions

### ML & RAG

- SentenceTransformers (all-MiniLM-L6-v2): Text embeddings
- Llama-3 8B Instruct (Q4): Local LLM for generation
- LangChain: RAG orchestration

### API & Deployment

- FastAPI: REST API endpoint
- Pydantic: Request/response validation
- Docker: Containerization
- AWS Lambda + API Gateway: Serverless deployment

## Project Structure

```
data/
├── raw_docs/          - Downloaded policy documents (HTML, Markdown, JSON metadata)
├── processed_chunks/  - Chunked policy text
└── metadata/          - Metadata seed files

ingestion/
├── load_docs.py       - Policy document downloader
├── chunk.py           - Chunking logic with structure preservation
└── embed.py           - Embedding generation and vector ingest

db/
├── models.py          - SQLAlchemy ORM models
├── session.py         - Database connection management
└── init.py            - Database initialization script

app/
├── main.py            - FastAPI application
├── schemas.py         - Pydantic request/response models
├── retrieval.py       - Hybrid retrieval implementation
├── generation.py      - LLM prompt construction and generation
└── citations.py       - Citation formatting

tests/
├── test_retrieval.py  - Retrieval correctness tests
├── test_sql_filters.py - Metadata filtering tests
├── test_grounding.py  - Citation validation tests
├── test_refusal.py    - Refusal behavior tests
└── test_api.py        - API endpoint tests

docker/
└── Dockerfile         - Container definition
```

## Setup Instructions

### 1. Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. PostgreSQL Setup

```bash
# Install PostgreSQL (macOS)
brew install postgresql@14

# Start PostgreSQL service
brew services start postgresql@14

# Create database
createdb ads_policy_rag

# Initialize schema
python -m db.init
```

### 3. Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://your_username@localhost:5432/ads_policy_rag
WEAVIATE_URL=http://localhost:8080
LLAMA_MODEL_PATH=./models/llama-3-8b-instruct.Q4_K_M.gguf
```

Replace `your_username` with your system username (run `whoami` to check).

## Implementation Steps

### Step 1: Data Collection (COMPLETED)

Download and structure policy documents from Google Ads.

**Implementation:**

- `ingestion/load_docs.py`: Web scraper with structure preservation
- Extracted 5 Google Ads policy documents
- Preserved HTML hierarchy (headers, bullets, sections)
- Generated metadata (doc_id, platform, category, title, sections)

**Technical concepts:**

- BeautifulSoup for HTML parsing
- Structure preservation for better chunking
- Metadata extraction for hybrid retrieval

**Output:**

- `.md` files: Structured policy text with section markers
- `_metadata.json`: Document metadata including section hierarchy
- `_raw.html`: Original HTML for reference

**Commands:**

```bash
python ingestion/load_docs.py
```

**Files created:**

```
data/raw_docs/
├── google_ads_base_hub.md
├── google_ads_base_hub_metadata.json
├── google_ads_misrepresentation.md
├── google_ads_misrepresentation_metadata.json
├── google_ads_restricted_products.md
├── google_ads_restricted_products_metadata.json
├── google_ads_prohibited_content.md
├── google_ads_prohibited_content_metadata.json
├── google_ads_editorial_technical.md
└── google_ads_editorial_technical_metadata.json
```

### Step 2: Metadata Design & PostgreSQL Schema (COMPLETED)

Define structured metadata schema and create PostgreSQL database.

**Implementation:**

- `db/models.py`: SQLAlchemy ORM models with enums
- `db/session.py`: Database connection and session management
- `db/init.py`: Schema initialization script

**Schema design:**

```python
PolicyChunk:
  - chunk_id (UUID, primary key)
  - doc_id (string, indexed, versioned with date)
  - chunk_index (integer)
  - chunk_text (text, source of truth)
  - policy_source (enum: google)
  - policy_section (string, indexed)
  - policy_section_level (string: H2, H3)
  - region (enum: global, us, eu, uk)
  - content_type (enum: ad_text, image, video, landing_page, general)
  - effective_date (datetime, nullable)
  - doc_url (string)
  - created_at (datetime)
```

**Architecture:**

PostgreSQL stores both metadata and canonical chunk text. Weaviate stores embeddings derived from this text. This design ensures:

- PostgreSQL is the source of truth for all chunk data
- Re-embedding, auditing, and debugging are possible without vector DB dependency
- Weaviate can be rebuilt from PostgreSQL at any time
- Both systems join on `chunk_id` during hybrid retrieval

**Key concepts:**

- Enums for type safety (PolicySource, Region, ContentType)
- Indexes on filterable columns for query performance
- UUID for globally unique identifiers
- Nullable effective_date for version tracking
- `region` and `content_type` currently default to GLOBAL/GENERAL; designed for future routing when region-specific policies are added

**Hybrid retrieval rationale:**

1. Vector search finds semantically similar chunks
2. SQL filters by region, content_type, policy_source
3. Combined: relevant + correctly filtered results

**Commands:**

```bash
# Create database
createdb ads_policy_rag

# Initialize schema
python -m db.init

# Verify table creation
psql ads_policy_rag -c "\d policy_chunks"
```

### Step 3: Chunking (COMPLETED)

Split policy documents into semantically coherent chunks while preserving document hierarchy.

**Implementation:**

- `ingestion/chunk.py`: Section-based chunking with hierarchy preservation
- Generated 67 chunks from 5 policy documents
- Maintained document structure through hierarchy prefixes

**Chunking strategy:**

- Section-based splitting: Use `[SECTION-H2]` and `[SECTION-H3]` markers
- Target size: 300-500 tokens per chunk
- Hierarchy preservation: Prefix each chunk with its section path (e.g., "[Prohibited Content > Alcohol]")
- Large section handling: Split sections exceeding token limit at sentence boundaries

**Technical concepts:**

- Semantic coherence: Keep related content together within sections
- Context preservation: Include hierarchy prefix for better retrieval
- Token estimation: Approximate token count using `words / 0.75` (assumes ~1.33 tokens/word for English text)
- Metadata propagation: Carry doc_id, platform, category to each chunk

**Design rationale:**

1. Policies are hierarchically structured (sections, subsections)
2. Splitting mid-section loses context
3. Section boundaries are natural semantic breaks
4. Hierarchy prefixes help LLM understand context during generation

**Output format (JSON):**

```json
{
  "chunk_id": "5f6826c1-e352-4996-8ca6-c9a704903e24",
  "doc_id": "google_prohibited_2025-12-22",
  "chunk_index": 0,
  "chunk_text": "[Prohibited Content > Alcohol]\n\nAlcohol-related ads must...",
  "policy_section": "Prohibited Content > Alcohol",
  "policy_section_level": "H3",
  "doc_url": "https://support.google.com/adspolicy/...",
  "platform": "google",
  "category": "prohibited"
}
```

**Critical design decisions:**

1. **Versioned doc_id**: `google_prohibited_2025-12-22` includes download date

   - Enables temporal policy tracking
   - Prevents overwriting when policies update
   - Critical for compliance auditing

2. **UUID chunk_id**: Generated at chunk creation (not database insertion)

   - Stable identifier across PostgreSQL and Weaviate
   - Enables reliable joins between metadata and vectors
   - UUID format: RFC 4122 compliant

3. **policy_section_level**: Stores H2 (top-level) or H3 (subsection)
   - Distinguishes between major policies and sub-rules
   - Enables hierarchical ranking in retrieval
   - Example: H2 "Restricted Content" vs H3 "Alcohol"

**Commands:**

```bash
python ingestion/chunk.py
```

**Files created:**

```
data/processed_chunks/
├── google_overview_chunks.json (28 chunks)
├── google_editorial_chunks.json (11 chunks)
├── google_misrepresentation_chunks.json (11 chunks)
├── google_restricted_chunks.json (8 chunks)
└── google_prohibited_chunks.json (9 chunks)
```

**Statistics:**

- Total chunks: 67
- Average chunk size: ~400 tokens
- All chunks preserve hierarchy context
- Ready for embedding generation (Step 4)

**Note on dataset size:**

Current corpus (67 chunks from 5 Google Ads documents) is intentionally minimal to validate architecture and demonstrate system capabilities. This focused scope enables:

- Clear demonstration of hybrid retrieval mechanics
- Fast iteration during development
- Proof of concept for production patterns

Future expansion paths:

- Meta Ads policies (~30-40 additional documents)
- Regional policy variations (EU GDPR, UK-specific rules)
- Appeals and enforcement guidelines
- Platform-specific best practices

The architecture is designed to scale from hundreds to millions of chunks without structural changes.

### Step 4: Embeddings & Vector Ingest (TODO)

Generate embeddings and store in Weaviate.

### Step 5: Hybrid Retrieval Logic (TODO)

Implement vector search + SQL filtering.

### Step 6: Generation Layer (TODO)

Build LLM prompts with grounding and citations.

### Step 7: API Layer (TODO)

Create FastAPI endpoint with validation.

### Step 8: Testing (TODO)

Implement comprehensive test suite.

### Step 9: Dockerization (TODO)

Package system in container.

### Step 10: README & Documentation (TODO)

Final documentation and example queries.

## Development Notes

### Database Schema Inspection

```bash
# List all tables
psql ads_policy_rag -c "\dt"

# Describe policy_chunks table
psql ads_policy_rag -c "\d policy_chunks"

# View enum types
psql ads_policy_rag -c "\dT+"
```

### Virtual Environment

```bash
# Activate (already active if in same session)
source venv/bin/activate

# Deactivate
deactivate
```

## Architecture Decisions

### PostgreSQL for Structured Metadata

- ACID compliance for data integrity
- Complex filtering with multiple conditions
- Excellent JSON support for flexible metadata
- Industry standard, proven at scale

### Weaviate for Vector Search

- Purpose-built for vector similarity search
- Fast approximate nearest neighbor search
- Scales to millions of vectors
- Production-ready with monitoring

### Hybrid Retrieval Approach

- Vector search alone: May return wrong region/type
- SQL search alone: Cannot understand semantic meaning
- Hybrid: Combines semantic relevance with structural constraints

### Local LLM (Llama-3)

- No API costs for inference
- Data privacy (no external API calls)
- Deterministic behavior for testing
- Efficient inference on Apple Silicon

## License

MIT
