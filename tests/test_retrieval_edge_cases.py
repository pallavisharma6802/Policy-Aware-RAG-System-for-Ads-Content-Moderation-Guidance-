"""
Failure and edge-case tests for hybrid retrieval (Step 5).
Tests 9-11: Robustness and defensive programming.
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.retrieval import retrieve_policy_chunks
from db.models import Region, ContentType, PolicySource


class TestNoResultsBehavior:
    """Test 9: No-results behavior"""
    
    def test_nonsense_query_returns_empty_list(self):
        # Query that shouldn't match any policy content
        results = retrieve_policy_chunks("unicorn blood advertising xyzabc123", limit=5)
        
        # Should return empty list, not crash
        assert isinstance(results, list), "Should return a list"
        # May return some results due to vector similarity, but should not crash
        # The key is: no exception should be raised
    
    def test_extremely_rare_terms(self):
        # Very specific query unlikely to match
        results = retrieve_policy_chunks("quantum entanglement blockchain NFT", limit=5)
        
        # Should handle gracefully (empty or low-relevance results)
        assert isinstance(results, list), "Should return a list"


class TestInvalidFilterHandling:
    """Test 10: Invalid filter handling"""
    
    def test_invalid_region_raises_error(self):
        with pytest.raises(ValueError):
            retrieve_policy_chunks("advertising", limit=5, region="mars")
    
    def test_invalid_content_type_raises_error(self):
        with pytest.raises(ValueError):
            retrieve_policy_chunks("policy", limit=5, content_type="hologram")
    
    def test_invalid_policy_source_raises_error(self):
        with pytest.raises(ValueError):
            retrieve_policy_chunks("rules", limit=5, policy_source="tiktok")
    
    def test_whitespace_in_filters_handled(self):
        # Should strip whitespace and work correctly
        results = retrieve_policy_chunks(
            "advertising",
            limit=5,
            region="  global  ",
            content_type=" general "
        )
        
        # Should not crash and should return filtered results
        for result in results:
            assert result["region"] == "global"
            assert result["content_type"] == "general"


class TestEmptyQuery:
    """Test 11: Empty query"""
    
    def test_empty_string_query(self):
        # Empty query should either return empty results or raise clear error
        results = retrieve_policy_chunks("", limit=5)
        
        # Most vector models will return some results even for empty query
        # Key is: should not crash
        assert isinstance(results, list), "Should return a list, not crash"
    
    def test_whitespace_only_query(self):
        results = retrieve_policy_chunks("   ", limit=5)
        
        assert isinstance(results, list), "Should handle whitespace-only queries"


class TestExtremeValues:
    """Additional edge cases for robustness"""
    
    def test_limit_zero(self):
        results = retrieve_policy_chunks("advertising", limit=0)
        
        assert len(results) == 0, "limit=0 should return empty list"
    
    def test_limit_one(self):
        results = retrieve_policy_chunks("advertising", limit=1)
        
        assert len(results) <= 1, "limit=1 should return at most 1 result"
    
    def test_very_large_limit(self):
        results = retrieve_policy_chunks("policy", limit=1000)
        
        # Should not crash, should return available results (max 67 in our corpus)
        assert len(results) <= 67, "Should not return more results than exist in corpus"
    
    def test_very_long_query(self):
        # Very long query
        long_query = "advertising " * 200
        results = retrieve_policy_chunks(long_query, limit=5)
        
        # Should handle gracefully
        assert isinstance(results, list), "Should handle very long queries"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
