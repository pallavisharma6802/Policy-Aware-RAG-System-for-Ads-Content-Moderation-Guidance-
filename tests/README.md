# Test Suite

Comprehensive test coverage for the Policy-Aware RAG System with 90 tests across 14 test files.

## Overview

90 tests covering retrieval, generation, API endpoints, database constraints, embeddings, and integration scenarios.

## Test Files

```
tests/
├── test_retrieval_core.py           # Core retrieval (16 tests)
├── test_retrieval_advanced.py       # Advanced retrieval (11 tests)
├── test_retrieval_edge_cases.py     # Edge cases (12 tests)
├── test_retrieval_integration.py    # Integration tests (10 tests)
├── test_generation_guardrails.py    # Generation safety (5 tests)
├── test_api_endpoints.py            # REST API (14 tests)
├── test_db_constraints.py           # Database rules (3 tests)
├── test_embedding_coverage.py       # Embedding validation (3 tests)
├── test_embedding_dimensions.py     # Vector dimensions (2 tests)
├── test_hybrid_retrieval_prep.py    # Hybrid setup (3 tests)
├── test_idempotent_ingestion.py     # Ingestion safety (2 tests)
├── test_rebuildability.py           # Data recovery (2 tests)
├── test_required_fields.py          # Schema validation (5 tests)
└── test_vector_id_alignment.py      # ID consistency (2 tests)
```

## Test Categories

### 1. Core Retrieval Tests (`test_retrieval_core.py`)

**16 tests** - Fundamental hybrid retrieval functionality

**Test classes:**

- `TestVectorRetrieval`: Basic vector search
- `TestRetrievalResultSchema`: Schema validation
- `TestSQLFiltering`: Metadata filtering (region, content_type, policy_source)
- `TestOverfetchMechanism`: Post-filtering result availability
- `TestVectorRankingPreservation`: Similarity ordering
- `TestHierarchyReranking`: Section level preferences (h2 vs h3)
- `TestScoreMonotonicity`: Score validation
- `TestDeterministicRetrieval`: Consistency checks

**Run:**

```bash
pytest tests/test_retrieval_core.py -v
```

**Example:**

```python
def test_region_filter_enforced():
    results = retrieve_policy_chunks(
        query="alcohol advertising",
        limit=5,
        region="Global"
    )
    for result in results:
        assert result["region"] == "Global"
```

### 2. Advanced Retrieval Tests (`test_retrieval_advanced.py`)

**11 tests** - Production-grade quality checks

**Test classes:**

- `TestRecallProtection`: Overfetch strategy validation
- `TestPolicyPathRelevance`: Semantic accuracy (alcohol → alcohol policy)
- `TestLatencyBudget`: Performance requirements (< 3s)
- `TestProductionReadiness`: Special characters, Unicode, concurrency

**Run:**

```bash
pytest tests/test_retrieval_advanced.py -v
```

**Example:**

```python
def test_alcohol_query_returns_alcohol_policy():
    results = retrieve_policy_chunks("Can I advertise alcohol?", limit=3)
    alcohol_found = any("alcohol" in r["policy_path"].lower() for r in results[:3])
    assert alcohol_found, "Top results should include alcohol policy"
```

### 3. Retrieval Edge Cases (`test_retrieval_edge_cases.py`)

**12 tests** - Robustness and error handling

**Test classes:**

- `TestNoResultsBehavior`: Nonsense queries, rare terms
- `TestInvalidFilterHandling`: Invalid enum values, whitespace handling
- `TestEmptyQuery`: Empty/whitespace queries
- `TestExtremeLimit`: Negative, zero, excessive limits
- `TestUnicodeAndSpecialChars`: International text, special characters

**Run:**

```bash
pytest tests/test_retrieval_edge_cases.py -v
```

**Example:**

```python
def test_invalid_region_raises_error():
    with pytest.raises(ValueError):
        retrieve_policy_chunks(
            query="test",
            limit=5,
            region="InvalidRegion"
        )
```

### 4. Retrieval Integration Tests (`test_retrieval_integration.py`)

**10 tests** - System-level consistency

**Test classes:**

- `TestPostgresWeaviateAlignment`: Database synchronization
- `TestChunkIdUniqueness`: No duplicate chunk IDs
- `TestMetadataConsistency`: Postgres ↔ Weaviate metadata matching
- `TestFilteredRetrievalIntegration`: End-to-end filtering

**Run:**

```bash
pytest tests/test_retrieval_integration.py -v
```

**Purpose:** Ensures PostgreSQL and Weaviate stay synchronized

### 5. Generation Guardrails Tests (`test_generation_guardrails.py`)

**5 tests** - LLM safety and hallucination prevention

**Key tests:**

- `test_generation_refuses_when_no_chunks`: No sources → refuse
- `test_generation_refuses_low_confidence`: Low scores → refuse
- `test_generation_requires_valid_citations`: Citations must exist
- `test_generation_success_has_citations`: Valid answers have citations
- `test_generation_includes_metrics`: Latency and token tracking

**Run:**

```bash
pytest tests/test_generation_guardrails.py -v
```

**Example:**

```python
def test_generation_refuses_when_no_chunks():
    response = generate_policy_response(
        query="quantum teleportation advertising regulations",
        limit=3
    )
    assert response.refused is True
    assert response.answer == ""
    assert response.refusal_reason is not None
```

### 6. API Endpoint Tests (`test_api_endpoints.py`)

**14 tests** - REST API contract validation

**Key tests:**

- `test_query_happy_path`: Valid request returns answer
- `test_query_refusal_path`: Out-of-scope triggers refusal
- `test_missing_query_field`: Validation catches missing fields
- `test_invalid_limit_negative`: Rejects invalid limits
- `test_invalid_limit_zero`: Rejects zero limit
- `test_invalid_limit_too_large`: Enforces max limit
- `test_query_too_short`: Enforces min query length
- `test_query_too_long`: Enforces max query length
- `test_html_page_loads`: Frontend serves correctly
- `test_health_endpoint`: Health check works
- `test_query_latency_under_threshold`: Performance acceptable
- `test_query_with_multiple_citations`: Multiple sources work
- `test_query_returns_metrics`: Latency and tokens tracked
- `test_query_with_optional_filters`: Region/content_type filtering

**Run:**

```bash
pytest tests/test_api_endpoints.py -v
```

**Example:**

```python
def test_query_happy_path():
    response = client.post(
        "/query",
        json={"query": "Can I advertise alcohol?", "limit": 5}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["refused"] is False
    assert len(data["answer"]) > 0
    assert isinstance(data["citations"], list)
```

### 7. Database Constraints Tests (`test_db_constraints.py`)

**3 tests** - Database integrity enforcement

**Key tests:**

- `test_duplicate_doc_id_chunk_index_fails`: Unique constraint on (doc_id, chunk_index)
- `test_uuid_primary_key_enforced`: Primary key validation
- `test_duplicate_chunk_id_fails`: Unique chunk_id constraint

**Run:**

```bash
pytest tests/test_db_constraints.py -v
```

**Purpose:** Ensures database schema constraints work correctly

### 8. Embedding Coverage Tests (`test_embedding_coverage.py`)

**3 tests** - Vector completeness validation

**Key tests:**

- `test_embedding_coverage`: All PostgreSQL chunks have Weaviate vectors
- `test_no_missing_embeddings`: No chunks missing from Weaviate
- `test_no_duplicate_vectors`: No duplicate vectors in Weaviate

**Run:**

```bash
pytest tests/test_embedding_coverage.py -v
```

**Purpose:** Validates PostgreSQL and Weaviate synchronization

### 9. Embedding Dimensions Tests (`test_embedding_dimensions.py`)

**2 tests** - Vector dimension validation

**Key tests:**

- `test_embedding_dimensions`: Vectors are 384-dimensional
- `test_model_dimension_matches`: Model output matches expected dimensions

**Run:**

```bash
pytest tests/test_embedding_dimensions.py -v
```

**Purpose:** Ensures embedding model produces correct vector dimensions

### 10. Hybrid Retrieval Prep Tests (`test_hybrid_retrieval_prep.py`)

**3 tests** - Weaviate setup validation

**Key tests:**

- `test_weaviate_object_id_equals_chunk_id`: Object IDs match chunk_ids
- `test_metadata_fields_stored`: All metadata fields present
- `test_filtering_by_metadata`: Weaviate filtering works

**Run:**

```bash
pytest tests/test_hybrid_retrieval_prep.py -v
```

**Purpose:** Validates Weaviate schema and metadata storage

### 11. Idempotent Ingestion Tests (`test_idempotent_ingestion.py`)

**2 tests** - Safe re-ingestion

**Key tests:**

- `test_idempotent_ingestion`: Running ingestion twice doesn't duplicate data
- `test_no_duplicate_chunks_exist`: No duplicate chunk_ids in database

**Run:**

```bash
pytest tests/test_idempotent_ingestion.py -v
```

**Purpose:** Ensures ingestion pipeline is safe to re-run

### 12. Rebuildability Tests (`test_rebuildability.py`)

**2 tests** - Data recovery capability

**Key tests:**

- `test_rebuildability`: Weaviate can be rebuilt from PostgreSQL
- `test_retrieval_after_rebuild`: Search works after rebuild

**Run:**

```bash
pytest tests/test_rebuildability.py -v
```

**Purpose:** Validates disaster recovery procedures

### 13. Required Fields Tests (`test_required_fields.py`)

**5 tests** - Schema validation

**Key tests:**

- `test_chunk_text_not_null`: chunk_text cannot be NULL
- `test_policy_path_not_null`: policy_path cannot be NULL
- `test_policy_source_enum_enforced`: Only valid PolicySource values
- `test_region_enum_enforced`: Only valid Region values
- `test_content_type_enum_enforced`: Only valid ContentType values

**Run:**

```bash
pytest tests/test_required_fields.py -v
```

**Purpose:** Ensures database schema enforces NOT NULL and enum constraints

### 14. Vector ID Alignment Tests (`test_vector_id_alignment.py`)

**2 tests** - ID consistency validation

**Key tests:**

- Vector IDs match chunk IDs between PostgreSQL and Weaviate
- No orphaned vectors or missing embeddings

**Run:**

```bash
pytest tests/test_vector_id_alignment.py -v
```

**Purpose:** Validates synchronization between databases

## Running Tests

### All Tests

```bash
# Run all 90 tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov=api --cov=ingestion --cov=db

# With HTML coverage report
pytest tests/ --cov --cov-report=html
open htmlcov/index.html
```

### Specific Test File

```bash
pytest tests/test_api_endpoints.py -v
```

### Specific Test

```bash
pytest tests/test_api_endpoints.py::test_query_happy_path -v
```

### By Pattern

```bash
# Run all retrieval tests
pytest tests/test_retrieval_*.py -v

# Run all generation tests
pytest tests/test_generation_*.py -v

# Run all embedding tests
pytest tests/test_embedding_*.py -v
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto
```

## Test Configuration

**pytest.ini:**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
```

## Performance

**Slowest tests:**

```
5.32s call     tests/test_generation_guardrails.py::test_generation_success_has_citations
2.15s call     tests/test_retrieval_advanced.py::test_retrieval_completes_within_budget
1.87s call     tests/test_api_endpoints.py::test_query_happy_path
```

**Optimization tips:**

- Generation tests take 2-5 seconds each (LLM inference)
- Use `pytest -n auto` for parallel execution
- Mock LLM for faster unit tests when testing non-generation logic

## Coverage

**Current coverage:**

- `app/`: ~85% (core logic well-tested)
- `api/`: ~90% (all endpoints covered)
- `ingestion/`: ~75% (main paths tested)
- `db/`: ~80% (models and queries tested)

**View coverage:**

```bash
pytest tests/ --cov --cov-report=term-missing
```

## Summary

**90 tests total**

**By category:**

- Retrieval: 49 tests (core + advanced + edge cases + integration)
- API: 14 tests
- Generation: 5 tests
- Database: 8 tests (constraints + required fields)
- Embeddings: 5 tests (coverage + dimensions)
- Integration: 9 tests (hybrid prep + idempotency + rebuildability + alignment)

**All tests passing:** 100%

## CI/CD Integration

**GitHub Actions example:**

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: "3.9"
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure all tests pass: `pytest tests/ -v`
3. Check coverage: `pytest tests/ --cov`
4. Add test documentation to this README

## Debugging Failed Tests

**View full output:**

```bash
pytest tests/ -v --tb=long
```

**Stop at first failure:**

```bash
pytest tests/ -x
```

**Run last failed tests:**

```bash
pytest tests/ --lf
```

**Enter debugger on failure:**

```bash
pytest tests/ --pdb
```
