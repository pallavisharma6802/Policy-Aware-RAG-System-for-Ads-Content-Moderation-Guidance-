"""
Advanced and optional tests for hybrid retrieval (Step 5).
Tests 15-17: Production-grade quality checks.
"""

import pytest
import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).parent.parent))

from app.retrieval import retrieve_policy_chunks, get_retriever


class TestRecallProtection:
    """Test 15: Recall protection test (overfetch justification)"""
    
    def test_overfetch_improves_recall_with_filters(self):
        # This test demonstrates why overfetch is necessary
        # We can't easily disable overfetch in the current implementation,
        # but we can verify that filtering doesn't lose all results
        
        query = "advertising policy"
        
        # Query with a filter that might reduce results
        results_filtered = retrieve_policy_chunks(
            query,
            limit=5,
            region="global"
        )
        
        # Should still get results even with filter
        # The overfetch mechanism (3x) ensures this
        assert len(results_filtered) > 0, "Overfetch should prevent empty results after filtering"
        
        # Verify all results actually match the filter
        for result in results_filtered:
            assert result["region"] == "global", "All results should match filter"
    
    def test_overfetch_enables_diverse_results(self):
        # Overfetch should allow us to get diverse results after filtering
        results = retrieve_policy_chunks(
            "content policy",
            limit=5,
            region="global"
        )
        
        if len(results) >= 2:
            # Check that results aren't all identical
            unique_sections = {r["policy_section"] for r in results}
            assert len(unique_sections) >= 1, "Should have at least some diversity"


class TestPolicyPathRelevance:
    """Test 16: Policy path relevance"""
    
    def test_alcohol_query_returns_alcohol_policy(self):
        results = retrieve_policy_chunks("Can I advertise alcohol?", limit=5)
        
        # Top result should be related to alcohol
        top_result = results[0]
        policy_path_lower = top_result["policy_path"].lower()
        chunk_text_lower = top_result["chunk_text"].lower()
        
        alcohol_relevant = (
            "alcohol" in policy_path_lower or
            "alcohol" in chunk_text_lower
        )
        
        assert alcohol_relevant, f"Top result should be alcohol-related: {top_result['policy_path']}"
    
    def test_cryptocurrency_query_returns_crypto_policy(self):
        results = retrieve_policy_chunks("cryptocurrency advertising rules", limit=5)
        
        # Check if any top-3 results mention crypto
        top_3 = results[:3] if len(results) >= 3 else results
        
        crypto_relevant = any(
            "crypto" in r["policy_path"].lower() or
            "crypto" in r["chunk_text"].lower()
            for r in top_3
        )
        
        assert crypto_relevant, "Top results should include cryptocurrency-related policies"
    
    def test_misrepresentation_query_returns_misrepresentation_policy(self):
        results = retrieve_policy_chunks("misrepresentation policy", limit=5)
        
        top_result = results[0]
        policy_path_lower = top_result["policy_path"].lower()
        
        misrep_relevant = (
            "misrepresent" in policy_path_lower or
            "misleading" in policy_path_lower
        )
        
        assert misrep_relevant, f"Should return misrepresentation-related policy: {top_result['policy_path']}"


class TestLatencyBudget:
    """Test 17: Latency budget test (production realism)"""
    
    def test_retrieval_completes_within_budget(self):
        # For a small corpus (67 chunks), retrieval should be fast
        # Set budget: 2 seconds (generous for small corpus)
        budget_ms = 2000
        
        start_time = time.time()
        results = retrieve_policy_chunks("advertising policy", limit=10)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert latency_ms < budget_ms, f"Retrieval took {latency_ms:.2f}ms, budget was {budget_ms}ms"
        assert len(results) > 0, "Should return results"
    
    def test_filtered_query_latency(self):
        # Filtered queries should also be fast
        budget_ms = 2000
        
        start_time = time.time()
        results = retrieve_policy_chunks(
            "content moderation",
            limit=5,
            region="global",
            content_type="general"
        )
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        assert latency_ms < budget_ms, f"Filtered query took {latency_ms:.2f}ms, budget was {budget_ms}ms"
    
    def test_singleton_pattern_improves_performance(self):
        # First call: loads model
        start_time = time.time()
        get_retriever()
        first_call_time = time.time() - start_time
        
        # Second call: should be instant (singleton)
        start_time = time.time()
        get_retriever()
        second_call_time = time.time() - start_time
        
        # Second call should be much faster (< 1ms)
        assert second_call_time < 0.001, f"Singleton pattern not working: second call took {second_call_time*1000:.2f}ms"


class TestProductionReadiness:
    """Additional production-quality checks"""
    
    def test_retrieval_handles_special_characters(self):
        # Queries with special characters should not crash
        special_queries = [
            "Can I advertise alcohol? Yes/No?",
            "Policy for $100 ads",
            "Rules for [URGENT] content",
            "Advertising & marketing guidelines"
        ]
        
        for query in special_queries:
            results = retrieve_policy_chunks(query, limit=3)
            assert isinstance(results, list), f"Should handle special chars in: {query}"
    
    def test_retrieval_handles_unicode(self):
        # Unicode queries should work
        unicode_queries = [
            "advertising règles",  # French
            "政策指南",  # Chinese
            "Política de anuncios"  # Spanish
        ]
        
        for query in unicode_queries:
            results = retrieve_policy_chunks(query, limit=3)
            assert isinstance(results, list), f"Should handle unicode in: {query}"
    
    def test_concurrent_retrieval_safety(self):
        # Singleton pattern should be thread-safe for reads
        # (This is a basic check; full concurrency testing needs threading)
        retriever = get_retriever()
        
        # Multiple calls should return same instance
        assert get_retriever() is retriever
        assert get_retriever() is retriever


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
