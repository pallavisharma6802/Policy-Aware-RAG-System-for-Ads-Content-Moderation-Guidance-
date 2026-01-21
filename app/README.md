# Application Core

Core RAG (Retrieval-Augmented Generation) logic for policy question answering.

## Overview

The `app/` module implements the core RAG pipeline: semantic retrieval, citation extraction, and LLM-based generation with hallucination prevention.

## Architecture

```
Query → Retrieval → Citations → Generation → Response
         ↓            ↓           ↓            ↓
      Weaviate    Validation   Ollama      Refusal
      PostgreSQL   Matching     LangChain   Detection
```

## Components

### 1. Retrieval (`retrieval.py`)

Hybrid retrieval combining semantic search and metadata filtering.

**Features:**

- **Semantic search**: Vector similarity via Weaviate
- **Keyword filtering**: Exact match on metadata (region, content_type, policy_source)
- **Score threshold**: Filters low-confidence matches (>0.25)
- **Database alignment**: Enriches results with PostgreSQL metadata

**Search flow:**

1. Embed query using sentence-transformers
2. Vector search in Weaviate
3. Apply metadata filters
4. Fetch full metadata from PostgreSQL
5. Sort by relevance score
6. Return top-k results

**RetrievalResult schema:**

```python
@dataclass
class RetrievalResult:
    chunk_id: str
    chunk_text: str
    policy_section: str
    policy_path: str
    policy_section_level: str
    doc_id: str
    doc_url: str
    policy_source: str
    region: str
    content_type: str
    score: float
```

**Usage:**

```python
from app.retrieval import retrieve_policy_chunks

results = retrieve_policy_chunks(
    query="gambling restrictions",
    limit=5
)

for result in results:
    print(f"{result.policy_path}: {result.score:.3f}")
    print(f"URL: {result.doc_url}")
```

**Configuration:**

```python
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
```

### 2. Citations (`citations.py`)

Citation extraction and validation to prevent hallucination.

**Key functions:**

**`extract_citations(answer: str) → List[str]`**

- Parses `SOURCE <chunk_id>` references from LLM output
- Returns list of cited chunk IDs
- Handles multiple citation formats

**`validate_citations(citations: List[str], sources: List[dict]) → List[str]`**

- Ensures all citations exist in retrieved sources
- Filters out hallucinated citations
- Returns only valid chunk IDs

**`build_citations(valid_chunk_ids: List[str], sources: List[dict]) → List[dict]`**

- Constructs citation objects for API response
- Includes chunk_id, policy_path, doc_id, doc_url
- Preserves order of appearance

**Citation flow:**

```
LLM Answer → Extract IDs → Validate Against Sources → Build Response
"SOURCE 123"    ["123"]      Check if 123 in sources    {chunk_id: "123", ...}
```


**Hallucination prevention:**

- Only citations matching retrieved sources are included
- Invalid citations are silently dropped
- Empty citations trigger refusal path

### 3. Generation (`generation.py`)

LLM-based answer generation with refusal detection.

**Generation pipeline:**

1. **Retrieve** relevant chunks
2. **Filter** by confidence score (>0.25)
3. **Format** sources with IDs
4. **Generate** answer with LLM
5. **Extract** citations from answer
6. **Validate** citations against sources
7. **Detect** refusal patterns
8. **Build** response object

**Refusal detection:**
Checks for phrases indicating insufficient information:

- "cannot provide"
- "not enough information"
- "sources do not contain"
- "unable to answer"
- etc.

**Response schema:**

```python
@dataclass
class PolicyResponse:
    answer: str                    # LLM-generated text
    refused: bool                  # True if LLM refused
    citations: List[dict]          # Citation objects
    refusal_reason: Optional[str]  # Why refused (if applicable)
    latency_ms: float             # Total response time
    num_tokens_generated: int     # Token count
```

**LLM configuration:**

```python
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

llm = Ollama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_HOST,
    temperature=0.05,  # Low temperature for factual answers
)
```

### 4. Schemas (`schemas.py`)

Data classes for type safety across the pipeline.

## Usage Examples

### Basic Query

```python
from app.generation import generate_policy_response

response = generate_policy_response(
    query="What are the gambling advertising rules?",
    limit=5
)

if response.refused:
    print(f"Refused: {response.refusal_reason}")
else:
    print(response.answer)
    for citation in response.citations:
        print(f"  - {citation['policy_path']}: {citation['doc_url']}")
```

### Filtered Query

```python
# Search only in specific region
response = generate_policy_response(
    query="alcohol advertising",
    limit=5,
    region="Global"
)
```

### Retrieval Only

```python
from app.retrieval import retrieve_policy_chunks

# Get chunks without LLM generation
chunks = retrieve_policy_chunks(
    query="financial services",
    limit=10,
    content_type="Advertising Policy"
)

for chunk in chunks:
    print(f"{chunk.policy_section} ({chunk.score:.3f})")
    print(f"  {chunk.chunk_text[:100]}...")
```

## Configuration

**Environment variables:**

```bash
# Weaviate
WEAVIATE_URL=http://localhost:8080

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:4b

# PostgreSQL (via db.session)
DATABASE_URL=postgresql://user:pass@localhost:5432/policy_rag
```

## Performance

**Typical latency breakdown:**

- Retrieval: 100-300ms
- LLM generation: 2000-5000ms
- Citation processing: <10ms
- **Total**: 2-5 seconds

**Optimization tips:**

- Use GPU for faster LLM inference
- Reduce `limit` parameter (fewer sources = faster)
- Use smaller LLM model (qwen2.5:1.5b vs 4b)
- Cache frequent queries

**Throughput:**

- Sequential: ~1-2 queries/minute
- With GPU: ~5-10 queries/minute
- Bottleneck: LLM inference time

## Error Handling

**No retrieval results:**

```python
# If no chunks retrieved above threshold
response.refused = True
response.refusal_reason = "No relevant policy sources found"
```

**LLM refuses to answer:**

```python
# If LLM detects insufficient information
response.refused = True
response.refusal_reason = "LLM determined sources insufficient"
```

**Invalid citations:**

```python
# Hallucinated citations are filtered out
# Only valid citations included in response
```

## Architecture Decisions

**Why hybrid retrieval?**

- Semantic search finds conceptually similar content
- Metadata filters ensure policy scope correctness
- Combines fuzzy matching with exact constraints

**Why citation validation?**

- LLMs can hallucinate source references
- Validation ensures all citations are real
- Builds trust in system outputs

**Why refusal detection?**

- Better than wrong answers
- Prevents overconfident responses
- User knows when to seek human review

**Why low temperature?**

- Factual domain requires consistency
- Reduces creative hallucination
- Improves citation accuracy

**Why LangChain?**

- Standardized LLM interface
- Easy model swapping
- Prompt template management
- Token counting utilities

## Integration

**Used by:**

- `api/main.py` - REST API endpoints
- `tests/test_generation_guardrails.py` - Generation safety tests
- `tests/test_retrieval_core.py` - Core retrieval tests
- `tests/test_retrieval_advanced.py` - Advanced retrieval tests
- `tests/test_retrieval_edge_cases.py` - Edge case tests
- `tests/test_retrieval_integration.py` - Integration tests
- `tests/test_api_endpoints.py` - End-to-end API tests

