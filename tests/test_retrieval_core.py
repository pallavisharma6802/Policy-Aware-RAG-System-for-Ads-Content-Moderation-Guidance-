"""
Core correctness tests for hybrid retrieval (Step 5).
Tests 1-8: Fundamental retrieval functionality.
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.retrieval import retrieve_policy_chunks, get_retriever


class TestVectorRetrieval:
    """Test 1: Vector retrieval returns results"""
    
    def test_vector_search_returns_results(self):
        results = retrieve_policy_chunks("Can I advertise alcohol?", limit=5)
        
        assert len(results) >= 1, "Should return at least one result"
        assert results[0]["chunk_text"] != "", "chunk_text should be non-empty"
        assert "score" in results[0], "Should have score (converted from distance)"
        assert results[0]["score"] > 0, "Score should be positive"


class TestRetrievalResultSchema:
    """Test 2: RetrievalResult schema completeness"""
    
    def test_result_has_all_required_fields(self):
        results = retrieve_policy_chunks("alcohol advertising", limit=1)
        
        assert len(results) > 0, "Need at least one result to test schema"
        
        result = results[0]
        required_fields = [
            "chunk_id",
            "chunk_text",
            "policy_section",
            "policy_path",
            "policy_section_level",
            "doc_id",
            "policy_source",
            "region",
            "content_type",
            "score"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
            assert result[field] is not None, f"Field {field} should not be None"
    
    def test_field_types_are_correct(self):
        results = retrieve_policy_chunks("policy", limit=1)
        result = results[0]
        
        assert isinstance(result["chunk_id"], str), "chunk_id should be string"
        assert isinstance(result["chunk_text"], str), "chunk_text should be string"
        assert isinstance(result["score"], (int, float)), "score should be numeric"
        assert isinstance(result["policy_section_level"], str), "policy_section_level should be string"


class TestSQLFiltering:
    """Test 3: SQL filtering actually filters (authoritative check)"""
    
    def test_region_filter_enforced(self):
        results = retrieve_policy_chunks("advertising policy", limit=10, region="global")
        
        assert len(results) > 0, "Should return results for global region"
        
        for result in results:
            assert result["region"] == "global", f"Expected region='global', got '{result['region']}'"
    
    def test_content_type_filter_enforced(self):
        results = retrieve_policy_chunks("advertising", limit=10, content_type="general")
        
        assert len(results) > 0, "Should return results for content_type=general"
        
        for result in results:
            assert result["content_type"] == "general", f"Expected content_type='general', got '{result['content_type']}'"
    
    def test_policy_source_filter_enforced(self):
        results = retrieve_policy_chunks("policy", limit=10, policy_source="google")
        
        assert len(results) > 0, "Should return results for policy_source=google"
        
        for result in results:
            assert result["policy_source"] == "google", f"Expected policy_source='google', got '{result['policy_source']}'"


class TestOverfetchMechanism:
    """Test 4: Overfetch prevents empty results after filtering"""
    
    def test_overfetch_provides_results_after_filtering(self):
        # Test with global region (should have results)
        results = retrieve_policy_chunks(
            "advertising rules",
            limit=5,
            region="global"
        )
        
        assert len(results) > 0, "Overfetch should provide results after filtering"
        assert len(results) <= 5, f"Should respect limit=5, got {len(results)}"
    
    def test_no_false_positives_in_filtered_results(self):
        # Query with strict filter
        results = retrieve_policy_chunks(
            "policy guidance",
            limit=3,
            region="global",
            content_type="general"
        )
        
        # All results must match BOTH filters
        for result in results:
            assert result["region"] == "global", "Filter constraint violated: region"
            assert result["content_type"] == "general", "Filter constraint violated: content_type"


class TestVectorRankingPreservation:
    """Test 5: Vector ranking preserved after SQL filter"""
    
    def test_results_ordered_by_similarity(self):
        results = retrieve_policy_chunks("alcohol advertising policy", limit=5)
        
        assert len(results) >= 2, "Need at least 2 results to test ordering"
        
        # Scores should be in descending order (higher = more similar)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"


class TestHierarchyReranking:
    """Test 6: Hierarchy reranking works"""
    
    def test_h3_preferred_when_prefer_specific_true(self):
        results = retrieve_policy_chunks(
            "misrepresentation",
            limit=5,
            prefer_specific=True
        )
        
        # Check that H3 sections appear early in results
        h3_positions = [i for i, r in enumerate(results) if r["policy_section_level"] == "H3"]
        h2_positions = [i for i, r in enumerate(results) if r["policy_section_level"] == "H2"]
        
        if h3_positions and h2_positions:
            assert min(h3_positions) < max(h2_positions), "H3 should appear before H2 when prefer_specific=True"
    
    def test_h2_preferred_when_prefer_specific_false(self):
        results = retrieve_policy_chunks(
            "misrepresentation",
            limit=5,
            prefer_specific=False
        )
        
        h3_positions = [i for i, r in enumerate(results) if r["policy_section_level"] == "H3"]
        h2_positions = [i for i, r in enumerate(results) if r["policy_section_level"] == "H2"]
        
        if h3_positions and h2_positions:
            assert min(h2_positions) < max(h3_positions), "H2 should appear before H3 when prefer_specific=False"


class TestScoreMonotonicity:
    """Test 7: Score monotonicity"""
    
    def test_scores_positive(self):
        results = retrieve_policy_chunks("advertising", limit=10)
        
        for result in results:
            assert result["score"] > 0, f"Score should be positive, got {result['score']}"
    
    def test_scores_descending(self):
        results = retrieve_policy_chunks("policy rules", limit=10)
        
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Scores should be in descending order"
    
    def test_no_invalid_scores(self):
        results = retrieve_policy_chunks("content moderation", limit=10)
        
        for result in results:
            score = result["score"]
            assert not (score != score), f"Score should not be NaN"  # NaN check
            assert score != float('inf'), "Score should not be infinity"
            assert score != float('-inf'), "Score should not be negative infinity"


class TestDeterministicRetrieval:
    """Test 8: Deterministic retrieval (same input → same output)"""
    
    def test_same_query_returns_same_results(self):
        query = "Can I advertise alcohol?"
        
        results1 = retrieve_policy_chunks(query, limit=5)
        results2 = retrieve_policy_chunks(query, limit=5)
        
        chunk_ids1 = [r["chunk_id"] for r in results1]
        chunk_ids2 = [r["chunk_id"] for r in results2]
        
        assert chunk_ids1 == chunk_ids2, "Same query should return same chunk_ids in same order"
    
    def test_deterministic_with_filters(self):
        query = "advertising policy"
        
        results1 = retrieve_policy_chunks(query, limit=3, region="global")
        results2 = retrieve_policy_chunks(query, limit=3, region="global")
        
        chunk_ids1 = [r["chunk_id"] for r in results1]
        chunk_ids2 = [r["chunk_id"] for r in results2]
        
        assert chunk_ids1 == chunk_ids2, "Filtered queries should be deterministic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
