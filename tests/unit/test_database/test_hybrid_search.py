"""
Unit tests for hybrid_search.py
Tests hybrid search functionality combining dense and sparse search methods.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from app.database.hybrid_search import hybrid_group_search, _rerank


class TestRerank:
    """Test _rerank function"""
    
    def setup_method(self):
        """Setup test data"""
        self.sample_results = [
            {
                "score": 0.8,
                "semantic_boost": 0.1,
                "metadata": {
                    "groupId": "group-1",
                    "tags": "파이썬, 프로그래밍, 스터디",
                    "category": "기술",
                    "location": "서울"
                }
            },
            {
                "score": 0.7,
                "semantic_boost": 0.0,
                "metadata": {
                    "groupId": "group-2",
                    "tags": "요리, 베이킹",
                    "category": "취미",
                    "location": "부산"
                }
            }
        ]
    
    def test_rerank_basic_scoring(self):
        """Test basic reranking by score"""
        query = "테스트 쿼리"
        result = _rerank(self.sample_results, query)
        
        # Should be sorted by total score (base_score + semantic_boost)
        assert len(result) == 2
        assert result[0]["metadata"]["groupId"] == "group-1"  # 0.8 + 0.1 = 0.9


class TestHybridGroupSearch:
    """Test hybrid_group_search function"""
    
    @patch('app.database.hybrid_search.search_similar_documents')
    @patch('app.database.hybrid_search.keyword_search_documents')
    def test_hybrid_search_basic(self, mock_keyword_search, mock_dense_search):
        """Test basic hybrid search functionality"""
        # Setup mocks
        mock_dense_search.return_value = [
            {
                "score": 0.9,
                "metadata": {"groupId": "group-1", "name": "파이썬 스터디"},
                "origin": "real"
            }
        ]
        
        mock_keyword_search.return_value = [
            {
                "score": 0.8,
                "metadata": {"groupId": "group-2", "name": "자바 스터디"},
                "origin": "real"
            }
        ]
        
        # Execute
        result = hybrid_group_search("프로그래밍 스터디", top_k=5)
        
        # Verify
        assert len(result) == 2
        
        # Verify all search methods were called
        assert mock_dense_search.call_count == 2  # group-info and group-synthetic
        assert mock_keyword_search.call_count == 2  # group-info and group-synthetic


if __name__ == "__main__":
    pytest.main([__file__])
