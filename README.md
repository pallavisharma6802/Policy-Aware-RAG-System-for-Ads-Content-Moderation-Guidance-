# Policy-Aware RAG System for Ads & Content Moderation Guidance

A production-ready Retrieval-Augmented Generation (RAG) system that provides policy explanation and guidance for Google Ads content moderation using semantic search and local LLM inference.

## Overview

This system answers policy questions by:

1. **Retrieving** relevant policy sections using hybrid search (semantic + metadata)
2. **Generating** grounded answers with an LLM
3. **Citing** sources with direct links to policy documents
4. **Refusing** to answer when sources are insufficient (hallucination prevention)

## Key Features

- **Hybrid Retrieval**: Vector search (Weaviate) + SQL filtering (PostgreSQL)
- **Citation-Backed Answers**: Every response includes source policy links
- **Refusal Logic**: Explicitly refuses when policies don't cover the question
- **Section-Specific URLs**: Automatic extraction of policy section URLs (no hardcoding)
- **Interactive UI**: Web interface for easy querying
- **Fully Dockerized**: One command deploys entire stack
- **90 Tests**: Comprehensive test coverage (100% passing)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Query                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────▼──────────┐
                │  FastAPI REST API    │
                │  (api/)              │
                └───────────┬──────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────▼────┐      ┌─────▼──────┐    ┌─────▼──────┐
    │Retrieval│      │ Generation │    │  Citations │
    │ (app/)  │      │   (app/)   │    │   (app/)   │
    └────┬────┘      └─────┬──────┘    └─────┬──────┘
         │                  │                  │
    ┌────▼────┐      ┌─────▼──────┐          │
    │Weaviate │      │   Ollama   │          │
    │Vectors  │      │    LLM     │          │
    └────┬────┘      └────────────┘          │
         │                                    │
         └──────────┬─────────────────────────┘
                    │
             ┌──────▼──────┐
             │ PostgreSQL  │
             │   (db/)     │
             └──────▲──────┘
                    │
            ┌───────┴───────┐
            │   Ingestion   │
            │  (ingestion/) │
            └───────────────┘
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Copy environment template
cp .env.docker .env

# 2. Start all services (PostgreSQL, Weaviate, Ollama, FastAPI)
docker-compose up -d

# 3. Monitor startup (first run takes 5-10 minutes to download model)
docker-compose logs -f fastapi

# 4. Access the application
open http://localhost:8000
```

### Option 2: Local Development

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Start services
# PostgreSQL (must be running on localhost:5432)
# Weaviate: docker-compose up -d weaviate
# Ollama: ollama serve

# 3. Initialize database
python -c "from db.session import init_db; init_db()"

# 4. Run ingestion pipeline
python -m ingestion.load_docs   # Download policy documents
python -m ingestion.chunk       # Chunk into sections
python -m ingestion.embed       # Generate embeddings & index

# 5. Start API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 6. Access the application
open http://localhost:8000
```

## Component Documentation

Detailed documentation for each component:

### Core Components

- **[`ingestion/`](ingestion/README.md)** - Data pipeline (download → chunk → embed)
- **[`app/`](app/README.md)** - RAG core logic (retrieval, generation, citations)
- **[`api/`](api/README.md)** - REST API and web interface
- **[`db/`](db/README.md)** - PostgreSQL schema and models
- **[`tests/`](tests/README.md)** - Test suite (90 tests, 100% passing)

### Deployment

- **[`DOCKER.md`](DOCKER.md)** - Docker quick reference
- **README Step 8** (below) - Full Docker documentation

## API Usage

### Query Endpoint

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Can I advertise alcohol?",
    "limit": 5
  }'
```

**Response:**

```json
{
  "answer": "Alcohol advertising is allowed but requires certification...",
  "refused": false,
  "citations": [
    {
      "chunk_id": "google_ads_overview_chunk_005",
      "policy_path": "Prohibited Content > Alcohol",
      "doc_id": "google_ads_overview",
      "doc_url": "https://support.google.com/adspolicy/answer/6012382"
    }
  ],
  "latency_ms": 2543.2,
  "num_tokens_generated": 87
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

```bash
# Run all 90 tests
pytest tests/ -v

# Run specific component tests
pytest tests/test_api_endpoints.py -v            # API tests (14)
pytest tests/test_generation_guardrails.py -v    # Generation tests (5)
pytest tests/test_retrieval_core.py -v           # Core retrieval tests (16)
pytest tests/test_retrieval_advanced.py -v       # Advanced retrieval tests (11)
pytest tests/test_retrieval_edge_cases.py -v     # Edge case tests (12)
pytest tests/test_retrieval_integration.py -v    # Integration tests (10)

# With coverage
pytest tests/ --cov --cov-report=html
open htmlcov/index.html
```

**Test Results:** All 90 tests passing (100%)

## Technology Stack

| Component            | Technology                               | Purpose                     |
| -------------------- | ---------------------------------------- | --------------------------- |
| **Database**         | PostgreSQL 15                            | Structured metadata storage |
| **Vector DB**        | Weaviate 1.23                            | Semantic search             |
| **Embeddings**       | sentence-transformers (all-MiniLM-L6-v2) | Text vectorization          |
| **LLM**              | Ollama + Qwen 2.5 (3B)                   | Answer generation           |
| **API**              | FastAPI + Uvicorn                        | REST API server             |
| **Frontend**         | Vanilla HTML/CSS/JS                      | Interactive web UI          |
| **ORM**              | SQLAlchemy                               | Database interactions       |
| **Orchestration**    | LangChain                                | RAG pipeline                |
| **Containerization** | Docker + Docker Compose                  | Deployment                  |

## System Stats

- **Documents**: ~5-10 policy documents
- **Chunks**: ~67 indexed sections
- **Vector Dimensions**: 384 (all-MiniLM-L6-v2)
- **Query Latency**: 2-5 seconds
- **Model Size**: Qwen 2.5 3B (~2GB)
- **Test Coverage**: ~80% code coverage

## Example Queries

**Successful queries:**

- "Can I advertise alcohol?"
- "What are the gambling advertising rules?"
- "Are financial products restricted?"
- "What content is prohibited?"

**Refusal examples (by design):**

- "What products are allowed to advertise?" (inverse question - policies describe restrictions, not allowances)
- "What is the meaning of life?" (out of scope)

## Project Structure

```
.
├── api/                # REST API & web interface
│   ├── main.py        # FastAPI app
│   ├── models.py      # Pydantic schemas
│   └── static/        # Web UI (HTML/CSS/JS)
│
├── app/                # Core RAG logic
│   ├── retrieval.py   # Hybrid search
│   ├── generation.py  # LLM generation
│   ├── citations.py   # Citation extraction
│   └── schemas.py     # Response models
│
├── ingestion/          # Data pipeline
│   ├── load_docs.py   # Document scraper
│   ├── chunk.py       # Text chunking
│   └── embed.py       # Embedding generation
│
├── db/                 # Database layer
│   ├── models.py      # SQLAlchemy models
│   └── session.py     # Connection management
│
├── tests/              # Test suite (90 tests)
│   ├── test_api_endpoints.py            # API tests (14)
│   ├── test_retrieval_core.py           # Core retrieval (16)
│   ├── test_retrieval_advanced.py       # Advanced retrieval (11)
│   ├── test_retrieval_edge_cases.py     # Edge cases (12)
│   ├── test_retrieval_integration.py    # Integration (10)
│   ├── test_generation_guardrails.py    # Generation (5)
│   ├── test_db_constraints.py           # Database (3)
│   ├── test_embedding_coverage.py       # Embeddings (3)
│   └── ... (6 more files)
│
├── data/               # Generated data (gitignored)
│   ├── metadata.json  # Document metadata
│   └── chunks.json    # Processed chunks
│
├── Dockerfile          # FastAPI container
├── docker-compose.yml  # Multi-service orchestration
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Development Steps (Completed)

All 8 steps are complete with full documentation:

### Step 1: Data Ingestion Pipeline

**Status:** COMPLETED  
**Documentation:** [ingestion/README.md](ingestion/README.md)

- Web scraping for policy documents
- Automated section-specific URL extraction
- HTML parsing and metadata extraction

### Step 2: Database Schema

**Status:** COMPLETED  
**Documentation:** [db/README.md](db/README.md)

- PostgreSQL tables: `policy_sources`, `policy_chunks`
- SQLAlchemy ORM models
- Database initialization

### Step 3: Document Chunking

**Status:** COMPLETED  
**Documentation:** [ingestion/README.md](ingestion/README.md)

- Section-based chunking (h1-h4 hierarchy)
- Dynamic URL assignment per section
- Policy path construction

### Step 4: Embedding & Vector Storage

**Status:** COMPLETED  
**Documentation:** [ingestion/README.md](ingestion/README.md)

- sentence-transformers embedding model
- Weaviate vector indexing
- 384-dimensional vectors

### Step 5: Hybrid Retrieval

**Status:** COMPLETED  
**Documentation:** [app/README.md](app/README.md)

- Semantic search via Weaviate
- Metadata filtering via PostgreSQL
- Score thresholding

### Step 6: LLM Generation & Citations

**Status:** COMPLETED  
**Documentation:** [app/README.md](app/README.md)

- Ollama + Qwen 2.5 integration
- Citation extraction and validation
- Refusal detection

### Step 7: API Layer

**Status:** COMPLETED  
**Documentation:** [api/README.md](api/README.md)

- FastAPI REST endpoints
- Interactive web UI
- Input validation
- 14 API tests (all passing)

### Step 8: Dockerization

**Status:** COMPLETED  
**Documentation:** See below + [DOCKER.md](DOCKER.md)

- Multi-service Docker Compose
- Automated startup script
- Production-ready deployment

## Step 8: Dockerization (COMPLETED)

Containerize the entire application stack with Docker Compose for production deployment.

### Quick Start

```bash
cp .env.docker .env
docker-compose up -d
docker-compose logs -f fastapi
```

### Architecture

```
Docker Compose Stack:
├─ PostgreSQL (5432)   - Persistent database
├─ Weaviate (8080)     - Vector search
├─ Ollama (11434)      - LLM inference
└─ FastAPI (8000)      - API & web UI

Networks: policy-rag-network (bridge)
Volumes: postgres_data, weaviate_data, ollama_data
```

### Services

**PostgreSQL** (postgres:15-alpine)

- Stores chunks and metadata
- Health check: `pg_isready`

**Weaviate** (semitechnologies/weaviate:1.23.0)

- Vector similarity search
- Health check: `/.well-known/ready`

**Ollama** (ollama/ollama:latest)

- Local LLM inference (qwen2.5:3b)
- Auto-downloads model on startup
- Health check: `/api/tags`

**FastAPI** (custom build)

- REST API and web interface
- Auto-runs ingestion pipeline
- Health check: `/health`

### Startup Flow

The `docker-entrypoint.sh` script automates:

1. Wait for PostgreSQL, Weaviate, Ollama
2. Pull Ollama model if needed
3. Initialize database tables
4. Download policy documents (if needed)
5. Chunk documents (if needed)
6. Generate embeddings (if needed)
7. Start Uvicorn server

### Configuration

Environment variables in `.env`:

```bash
# Database
POSTGRES_DB=policy_rag
POSTGRES_USER=policy_user
POSTGRES_PASSWORD=policy_pass

# LLM
OLLAMA_MODEL=qwen2.5:3b

# Application
LOG_LEVEL=INFO
```

### Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f [service]

# Check status
docker-compose ps

# Stop services
docker-compose stop

# Stop and remove (keeps data)
docker-compose down

# Stop and remove all (deletes data)
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build fastapi
```

### Production Checklist

- [ ] Change default passwords
- [ ] Restrict CORS origins
- [ ] Enable HTTPS/TLS
- [ ] Add rate limiting
- [ ] Configure resource limits
- [ ] Set up monitoring
- [ ] Enable automatic backups
- [ ] Use secrets management

For detailed Docker documentation, see [DOCKER.md](DOCKER.md).

**Built with Python, FastAPI, PostgreSQL, Weaviate, and Ollama**
