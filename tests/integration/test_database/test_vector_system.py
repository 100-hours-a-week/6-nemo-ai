"""
Integration tests for the vector search system.
Migrated from src/tests/test_vector_system.py
"""

import pytest
import sys
import os
from typing import List, Dict
from pprint import pprint
import time

# Import from app instead of src
try:
    from app.database.vector.vector_searcher import (
        search_similar_documents,
        keyword_search_documents,
        get_user_joined_group_ids,
        get_system_stats,
        category_discovery,
        semantic_booster
    )
except ImportError:
    pytest.skip("Vector database not available", allow_module_level=True)


@pytest.mark.integration
@pytest.mark.vector
class TestVectorSystem:
    """Integration test suite for vector search system."""

    def test_user_exclusion(self):
        """Test user group exclusion functionality."""
        test_users = ["20", "15", "u2", "u5"]
        
        for user_id in test_users:
            joined_groups = get_user_joined_group_ids(user_id)
            assert isinstance(joined_groups, (list, set))
            # Validate that we get valid group IDs
            if joined_groups:
                for group_id in list(joined_groups)[:5]:  # Check first 5
                    assert group_id is not None

    def test_category_discovery(self):
        """Test vector-based category discovery."""
        test_queries = [
            "축구 모임 찾아요",
            "개발 스터디 하고 싶어요", 
            "독서 모임 참여하고 싶습니다",
            "요리 배우고 싶어요",
            "봉사활동 같이 해요"
        ]
        
        for query in test_queries:
            category_matches = category_discovery.infer_query_categories(query)
            assert isinstance(category_matches, list)
            # Should return at least some categories with scores
            for cat, score in category_matches[:3]:
                assert isinstance(cat, str)
                assert isinstance(score, (int, float))
                assert 0 <= score <= 1

    def test_semantic_enhancement(self):
        """Test semantic term relationships."""
        test_terms = ["축구", "풋살", "개발", "프로그래밍", "요리", "음식"]
        
        for term in test_terms:
            related = semantic_booster.get_related_terms(term, threshold=0.7)
            if related:
                assert isinstance(related, dict)
                for rel_term, score in related.items():
                    assert isinstance(rel_term, str)
                    assert isinstance(score, (int, float))
                    assert 0 <= score <= 1

    @pytest.mark.parametrize("scenario", [
        {
            "name": "Sports Query", 
            "query": "풋살 같이 하실분",
            "user_id": "20",
            "expected_categories": ["sports", "football", "soccer"]
        },
        {
            "name": "Tech Query",
            "query": "백엔드 개발 공부하고 싶어요", 
            "user_id": "15",
            "expected_categories": ["programming", "development", "tech"]
        },
        {
            "name": "Cultural Query",
            "query": "영화 보고 토론해요",
            "user_id": None,
            "expected_categories": ["culture", "movies", "discussion"]
        }
    ])
    def test_search_scenarios(self, scenario):
        """Test various search scenarios with parameterized data."""
        query = scenario["query"]
        user_id = scenario["user_id"]
        
        # Test vector search
        start_time = time.time()
        vector_results = search_similar_documents(
            query, 
            top_k=3, 
            user_id=user_id
        )
        vector_time = time.time() - start_time
        
        # Validate results structure
        assert isinstance(vector_results, list)
        assert len(vector_results) <= 3
        assert vector_time < 5.0  # Should complete within 5 seconds
        
        for result in vector_results:
            assert "metadata" in result
            assert "score" in result
            assert "text" in result
            assert isinstance(result["score"], (int, float))
            assert 0 <= result["score"] <= 1
        
        # Test keyword search for comparison
        start_time = time.time()
        keyword_results = keyword_search_documents(
            query,
            top_k=3,
            user_id=user_id
        )
        keyword_time = time.time() - start_time
        
        # Validate keyword results
        assert isinstance(keyword_results, list)
        assert len(keyword_results) <= 3
        assert keyword_time < 5.0

    @pytest.mark.parametrize("edge_case", [
        {"name": "Empty Query", "query": "", "user_id": None},
        {"name": "Very Short Query", "query": "축구", "user_id": "20"},
        {"name": "English Query", "query": "soccer team", "user_id": None},
        {"name": "Mixed Language", "query": "programming 스터디", "user_id": "15"},
        {"name": "Special Characters", "query": "모임!@#$%^&*()", "user_id": None},
    ])
    def test_edge_cases(self, edge_case):
        """Test edge cases and error handling."""
        query = edge_case["query"]
        user_id = edge_case["user_id"]
        
        # Should not raise exceptions for edge cases
        try:
            results = search_similar_documents(
                query,
                top_k=2,
                user_id=user_id
            )
            
            # Even for edge cases, should return valid structure
            assert isinstance(results, list)
            assert len(results) <= 2
            
            for result in results:
                assert "metadata" in result
                assert "score" in result
                assert "text" in result
                
        except Exception as e:
            # If it raises an exception, it should be a known/expected one
            assert "empty" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.slow
    def test_performance(self):
        """Test system performance."""
        queries = [
            "축구 모임",
            "개발 스터디", 
            "맛집 탐방",
            "영화 감상",
            "봉사활동"
        ]
        
        # Vector search timing
        start_time = time.time()
        for query in queries:
            search_similar_documents(query, top_k=5)
        vector_total = time.time() - start_time
        
        # Keyword search timing  
        start_time = time.time()
        for query in queries:
            keyword_search_documents(query, top_k=5)
        keyword_total = time.time() - start_time
        
        # Performance assertions
        avg_vector_time = vector_total / len(queries)
        avg_keyword_time = keyword_total / len(queries)
        
        assert avg_vector_time < 2.0  # Should be under 2 seconds per query
        assert avg_keyword_time < 1.0  # Keyword should be faster
        
        print(f"Vector Search Average: {avg_vector_time:.3f}s")
        print(f"Keyword Search Average: {avg_keyword_time:.3f}s")

    def test_system_health(self):
        """Test overall system health."""
        stats = get_system_stats()
        
        # Validate stats structure
        assert isinstance(stats, dict)
        
        # Check required fields
        required_fields = ["system_ready"]
        for field in required_fields:
            assert field in stats
        
        # If system is ready, other components should be working
        if stats.get("system_ready"):
            assert isinstance(stats.get("semantic_terms", 0), int)
            assert isinstance(stats.get("categories_discovered", 0), int)


@pytest.mark.integration
def test_comprehensive_vector_system():
    """Run comprehensive test for the vector system."""
    # This function serves as an entry point for running all vector tests
    # and can be called from CI/CD pipelines
    
    test_suite = TestVectorSystem()
    
    # Run core functionality tests
    test_suite.test_system_health()
    test_suite.test_user_exclusion()
    test_suite.test_category_discovery()
    test_suite.test_semantic_enhancement()
    
    print("✅ Comprehensive vector system test completed")


if __name__ == "__main__":
    # Allow running the test directly
    pytest.main([__file__, "-v"])
