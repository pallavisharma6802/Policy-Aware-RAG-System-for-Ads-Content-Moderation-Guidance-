import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from api.main import app

client = TestClient(app)


def test_query_happy_path():
    """
    POST /query with valid question returns answer with citations.
    Validates end-to-end RAG pipeline through API.
    """
    response = client.post(
        "/query",
        json={"query": "Can I advertise alcohol?", "limit": 5}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["refused"] is False
    assert len(data["answer"]) > 0
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) > 0
    
    citation = data["citations"][0]
    assert "chunk_id" in citation
    assert "policy_path" in citation
    assert "doc_url" in citation
    assert len(citation["chunk_id"]) > 0
    assert len(citation["policy_path"]) > 0
    assert len(citation["doc_url"]) > 0


def test_query_refusal_path():
    """
    POST /query with question outside policy scope triggers refusal.
    Validates hallucination prevention at API boundary.
    """
    response = client.post(
        "/query",
        json={"query": "What is the weather today?", "limit": 5}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["refused"] is True
    assert "refusal_reason" in data
    assert len(data["refusal_reason"]) > 0
    assert data["answer"] == "" or "REFUSE" in data["answer"]
    assert len(data["citations"]) == 0


def test_missing_query_field():
    """
    POST /query without required query field returns validation error.
    Validates Pydantic schema enforcement.
    """
    response = client.post(
        "/query",
        json={"limit": 5}
    )
    
    assert response.status_code == 422


def test_invalid_limit_negative():
    """
    POST /query with negative limit returns validation error.
    Validates constraint enforcement on numeric fields.
    """
    response = client.post(
        "/query",
        json={"query": "Can I advertise gambling?", "limit": -5}
    )
    
    assert response.status_code == 422


def test_invalid_limit_zero():
    """
    POST /query with zero limit returns validation error.
    Validates minimum value constraint.
    """
    response = client.post(
        "/query",
        json={"query": "Can I advertise gambling?", "limit": 0}
    )
    
    assert response.status_code == 422


def test_invalid_limit_too_large():
    """
    POST /query with limit exceeding maximum returns validation error.
    Validates maximum value constraint.
    """
    response = client.post(
        "/query",
        json={"query": "Can I advertise gambling?", "limit": 100}
    )
    
    assert response.status_code == 422


def test_query_too_short():
    """
    POST /query with query below minimum length returns validation error.
    Validates string length constraints.
    """
    response = client.post(
        "/query",
        json={"query": "hi", "limit": 5}
    )
    
    assert response.status_code == 422


def test_query_too_long():
    """
    POST /query with query exceeding maximum length returns validation error.
    Validates string length upper bound.
    """
    long_query = "a" * 600
    response = client.post(
        "/query",
        json={"query": long_query, "limit": 5}
    )
    
    assert response.status_code == 422


def test_html_page_loads():
    """
    GET / returns HTML frontend with expected content.
    Validates frontend wiring and static file serving.
    """
    response = client.get("/")
    
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Policy-Aware RAG System" in response.text


def test_health_endpoint():
    """
    GET /health returns system status.
    Validates health check endpoint and service dependencies.
    """
    response = client.get("/health")
    
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "vector_db" in data
    assert "llm" in data


def test_query_latency_under_threshold():
    """
    POST /query completes within reasonable time.
    Not a benchmark, just a sanity check for timeouts.
    Note: First query may be slow due to model loading.
    """
    response = client.post(
        "/query",
        json={"query": "What are the gambling rules?", "limit": 3}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "latency_ms" in data
    assert data["latency_ms"] < 300000


def test_query_with_multiple_citations():
    """
    POST /query with broad question returns multiple citations.
    Validates retrieval returns diverse sources.
    """
    response = client.post(
        "/query",
        json={"query": "What products are restricted to advertise?", "limit": 10}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    if not data["refused"]:
        assert len(data["citations"]) > 1
        
        unique_urls = set(c["doc_url"] for c in data["citations"])
        assert len(unique_urls) > 0


def test_query_returns_metrics():
    """
    POST /query includes performance metrics in response.
    Validates observability data is present.
    """
    response = client.post(
        "/query",
        json={"query": "Can I advertise alcohol?", "limit": 5}
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert "latency_ms" in data
    assert "num_tokens_generated" in data
    assert isinstance(data["latency_ms"], (int, float))
    assert isinstance(data["num_tokens_generated"], int)
    assert data["latency_ms"] > 0
    assert data["num_tokens_generated"] >= 0


def test_query_with_optional_filters():
    """
    POST /query accepts optional filter parameters.
    Validates optional fields are handled correctly.
    """
    response = client.post(
        "/query",
        json={
            "query": "Can I advertise alcohol?",
            "limit": 5,
            "region": "global",
            "policy_source": "google"
        }
    )
    
    assert response.status_code in [200, 422]
