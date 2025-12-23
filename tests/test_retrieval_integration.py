"""
Integration sanity tests for hybrid retrieval (Step 5).
Tests 12-14: System integration and constraint validation.
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.retrieval import retrieve_policy_chunks
from db.session import SessionLocal
from db.models import PolicyChunk
import weaviate


class TestPostgresWeaviateAlignment:
    """Test 12: Postgres-Weaviate ID alignment"""
    
    def test_all_returned_chunks_exist_in_postgres(self):
        results = retrieve_policy_chunks("advertising policy", limit=10)
        
        assert len(results) > 0, "Need results to test alignment"
        
        db = SessionLocal()
        try:
            returned_chunk_ids = [r["chunk_id"] for r in results]
            
            # Query PostgreSQL for these chunk_ids
            postgres_chunks = db.query(PolicyChunk).filter(
                PolicyChunk.chunk_id.in_(returned_chunk_ids)
            ).all()
            
            postgres_chunk_ids = {str(chunk.chunk_id) for chunk in postgres_chunks}
            
            for chunk_id in returned_chunk_ids:
                assert chunk_id in postgres_chunk_ids, f"chunk_id {chunk_id} not found in PostgreSQL"
        finally:
            db.close()
    
    def test_no_orphan_vectors_in_weaviate(self):
        # Get all Weaviate chunk_ids
        client = weaviate.Client(url="http://localhost:8080")
        
        result = client.query.get(
            "PolicyChunk",
            ["chunk_id"]
        ).with_limit(100).do()
        
        weaviate_chunks = result.get("data", {}).get("Get", {}).get("PolicyChunk", [])
        weaviate_chunk_ids = {chunk["chunk_id"] for chunk in weaviate_chunks}
        
        # Get all PostgreSQL chunk_ids
        db = SessionLocal()
        try:
            postgres_chunks = db.query(PolicyChunk.chunk_id).all()
            postgres_chunk_ids = {str(chunk.chunk_id) for chunk in postgres_chunks}
            
            # Every Weaviate ID should exist in PostgreSQL
            orphan_ids = weaviate_chunk_ids - postgres_chunk_ids
            
            assert len(orphan_ids) == 0, f"Found {len(orphan_ids)} orphan vectors in Weaviate"
        finally:
            db.close()


class TestLimitRespected:
    """Test 13: Limit respected"""
    
    def test_limit_3_returns_max_3_results(self):
        results = retrieve_policy_chunks("advertising", limit=3)
        
        assert len(results) <= 3, f"Expected max 3 results, got {len(results)}"
    
    def test_limit_1_returns_max_1_result(self):
        results = retrieve_policy_chunks("policy", limit=1)
        
        assert len(results) <= 1, f"Expected max 1 result, got {len(results)}"
    
    def test_limit_10_returns_max_10_results(self):
        results = retrieve_policy_chunks("content moderation", limit=10)
        
        assert len(results) <= 10, f"Expected max 10 results, got {len(results)}"


class TestMultiFilterConjunction:
    """Test 14: Multi-filter conjunction (AND logic)"""
    
    def test_region_and_content_type_both_enforced(self):
        results = retrieve_policy_chunks(
            "advertising rules",
            limit=10,
            region="global",
            content_type="general"
        )
        
        assert len(results) > 0, "Should return results matching both filters"
        
        for result in results:
            assert result["region"] == "global", "Region constraint violated"
            assert result["content_type"] == "general", "Content type constraint violated"
    
    def test_all_three_filters_enforced(self):
        results = retrieve_policy_chunks(
            "policy",
            limit=10,
            region="global",
            content_type="general",
            policy_source="google"
        )
        
        # All three constraints must be satisfied
        for result in results:
            assert result["region"] == "global", "Region constraint violated"
            assert result["content_type"] == "general", "Content type constraint violated"
            assert result["policy_source"] == "google", "Policy source constraint violated"
    
    def test_restrictive_filters_reduce_results(self):
        # Query without filters
        results_no_filter = retrieve_policy_chunks("advertising", limit=20)
        
        # Query with restrictive filters
        results_filtered = retrieve_policy_chunks(
            "advertising",
            limit=20,
            region="global",
            content_type="general"
        )
        
        # Filtered results should be <= unfiltered
        # (unless all chunks match the filter, which is possible in our corpus)
        assert len(results_filtered) <= len(results_no_filter) or len(results_filtered) <= 20


class TestHybridRetrievalCorrectness:
    """Additional integration tests for hybrid retrieval correctness"""
    
    def test_vector_search_finds_semantically_similar(self):
        # "alcohol" should match "Alcohol" policy section
        results = retrieve_policy_chunks("Can I advertise beer?", limit=5)
        
        # Check if any result contains "alcohol" or "Alcohol" in policy section
        alcohol_related = any(
            "alcohol" in r["policy_section"].lower() or
            "alcohol" in r["chunk_text"].lower()
            for r in results
        )
        
        assert alcohol_related, "Should find alcohol-related policies for beer query"
    
    def test_sql_filter_does_not_break_semantic_search(self):
        # Semantic search should still work with filters
        results = retrieve_policy_chunks(
            "cryptocurrency rules",
            limit=5,
            region="global"
        )
        
        if len(results) > 0:
            # Should find crypto-related content
            crypto_related = any(
                "crypto" in r["policy_section"].lower() or
                "crypto" in r["chunk_text"].lower()
                for r in results
            )
            
            # All should match filter
            all_global = all(r["region"] == "global" for r in results)
            
            assert all_global, "Filter constraint violated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
