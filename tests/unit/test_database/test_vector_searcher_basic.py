"""
Unit tests for Vector Searcher functionality.
Tests for app/database/vector_searcher.py
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Import from app instead of src
try:
    from app.database.vector_searcher import (
        VectorBasedCategoryDiscovery,
        SemanticBooster,
        get_user_joined_group_ids,
        get_random_group_for_user,
        search_similar_documents,
        get_system_stats
    )
except ImportError:
    pytest.skip("Vector searcher module not available", allow_module_level=True)


@pytest.mark.unit
class TestVectorBasedCategoryDiscovery:
    """Unit tests for VectorBasedCategoryDiscovery class."""

    def test_category_discovery_initialization(self):
        """Test VectorBasedCategoryDiscovery initialization."""
        discovery = VectorBasedCategoryDiscovery()
        
        assert discovery.similarity_threshold == 0.7
        assert discovery.category_cache == {}
        assert discovery.category_embeddings == {}

    def test_category_discovery_custom_threshold(self):
        """Test VectorBasedCategoryDiscovery with custom threshold."""
        discovery = VectorBasedCategoryDiscovery(similarity_threshold=0.8)
        
        assert discovery.similarity_threshold == 0.8

    @patch('app.database.vector_searcher.embed')
    def test_discover_categories_from_data_empty(self, mock_embed):
        """Test category discovery with empty metadata."""
        discovery = VectorBasedCategoryDiscovery()
        
        metadatas = []
        result = discovery.discover_categories_from_data(metadatas)
        
        assert result == {}
        mock_embed.assert_not_called()

    @patch('app.database.vector_searcher.embed')
    def test_discover_categories_embedding_failure(self, mock_embed):
        """Test category discovery when embedding fails."""
        discovery = VectorBasedCategoryDiscovery()
        
        mock_embed.side_effect = Exception("Embedding failed")
        
        metadatas = [{"category": "sports"}]
        result = discovery.discover_categories_from_data(metadatas)
        
        assert result == {}

    @patch('app.database.vector_searcher.embed')
    def test_infer_query_categories_empty_embeddings(self, mock_embed):
        """Test query category inference with no category embeddings."""
        discovery = VectorBasedCategoryDiscovery()
        
        result = discovery.infer_query_categories("football match")
        
        assert result == []
        mock_embed.assert_not_called()


@pytest.mark.unit
class TestSemanticBooster:
    """Unit tests for SemanticBooster class."""

    def test_semantic_booster_initialization(self):
        """Test SemanticBooster initialization."""
        booster = SemanticBooster()
        
        assert booster.term_embeddings == {}
        assert booster.semantic_clusters == {}

    def test_extract_meaningful_terms(self):
        """Test meaningful term extraction."""
        booster = SemanticBooster()
        
        # Test Korean and English mixed text
        text = "안녕하세요! Hello world. 축구를 좋아해요. Programming is fun."
        terms = booster._extract_meaningful_terms(text)
        
        # Should extract meaningful terms and filter stopwords
        assert len(terms) > 0
        assert "programming" in terms


@pytest.mark.unit
class TestUserJoinedGroups:
    """Unit tests for user joined groups functionality."""

    @patch('app.database.vector_searcher.get_chroma_client')
    @patch('app.database.vector_searcher.logger')
    def test_get_user_joined_group_ids_success(self, mock_logger, mock_client):
        """Test successful retrieval of user joined group IDs."""
        # Mock ChromaDB client and collection
        mock_collection = Mock()
        mock_collection.count.return_value = 100
        mock_collection.get.return_value = {
            "metadatas": [
                {"groupId": "group1"},
                {"groupId": "group2"},
                {"groupId": "group3"}
            ]
        }
        
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance
        
        result = get_user_joined_group_ids("test_user")
        
        assert isinstance(result, set)
        assert "group1" in result
        assert "group2" in result
        assert "group3" in result

    @patch('app.database.vector_searcher.get_chroma_client')
    @patch('app.database.vector_searcher.logger')
    def test_get_user_joined_group_ids_exception_handling(self, mock_logger, mock_client):
        """Test exception handling in get_user_joined_group_ids."""
        mock_client.side_effect = Exception("Database connection failed")
        
        result = get_user_joined_group_ids("test_user")
        
        assert isinstance(result, set)
        assert len(result) == 0
        mock_logger.warning.assert_called()


@pytest.mark.unit
class TestRandomGroupRecommendation:
    """Unit tests for random group recommendation functionality."""

    @patch('app.database.vector_searcher.get_chroma_client')
    @patch('app.database.vector_searcher.get_user_joined_group_ids')
    @patch('app.database.vector_searcher.logger')
    @patch('random.choice')
    def test_get_random_group_for_user_success(self, mock_choice, mock_logger, mock_joined, mock_client):
        """Test successful random group recommendation."""
        # Mock user joined groups
        mock_joined.return_value = {"group1", "group2"}
        
        # Mock ChromaDB collection
        mock_collection = Mock()
        mock_collection.count.return_value = 100
        mock_collection.get.return_value = {
            "documents": ["Group 3 description", "Group 4 description"],
            "metadatas": [
                {"groupId": "group3", "category": "sports"},
                {"groupId": "group4", "category": "study"}
            ]
        }
        
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance
        
        # Mock random choice
        mock_choice.return_value = {
            "text": "Group 3 description",
            "metadata": {"groupId": "group3", "category": "sports"}
        }
        
        result = get_random_group_for_user("test_user")
        
        assert result is not None
        assert result["metadata"]["groupId"] == "group3"
        assert result["score"] == 0.5
        assert result["origin"] == "random"

    @patch('app.database.vector_searcher.get_chroma_client')
    @patch('app.database.vector_searcher.logger')
    def test_get_random_group_for_user_exception_handling(self, mock_logger, mock_client):
        """Test random group recommendation exception handling."""
        mock_client.side_effect = Exception("Database error")
        
        result = get_random_group_for_user("test_user")
        
        assert result is None
        mock_logger.exception.assert_called()


@pytest.mark.unit
class TestSearchSimilarDocuments:
    """Unit tests for search_similar_documents functionality."""

    @patch('app.database.vector_searcher.get_chroma_client')
    @patch('app.database.vector_searcher.logger')
    def test_search_similar_documents_exception_handling(self, mock_logger, mock_client):
        """Test search similar documents exception handling."""
        mock_client.side_effect = Exception("Search failed")
        
        result = search_similar_documents("test query")
        
        assert result == []
        mock_logger.exception.assert_called()


@pytest.mark.unit
class TestSystemStats:
    """Unit tests for system statistics functionality."""

    @patch('app.database.vector_searcher.category_discovery')
    @patch('app.database.vector_searcher.semantic_booster')
    def test_get_system_stats_success(self, mock_booster, mock_discovery):
        """Test successful system stats retrieval."""
        # Mock category discovery
        mock_discovery.category_embeddings = {"sports": True, "study": True}
        
        # Mock semantic booster
        mock_booster.term_embeddings = {"term1": True, "term2": True, "term3": True}
        mock_booster.semantic_clusters = {
            "term1": {"related1": 0.9},
            "term2": {"related2": 0.8, "related3": 0.7}
        }
        
        result = get_system_stats()
        
        assert result["categories_discovered"] == 2
        assert result["semantic_terms"] == 3
        assert result["semantic_clusters"] == 2
        assert result["total_relationships"] == 3  # 1 + 2
        assert result["system_ready"] is True

    @patch('app.database.vector_searcher.category_discovery')
    @patch('app.database.vector_searcher.semantic_booster')
    @patch('app.database.vector_searcher.logger')
    def test_get_system_stats_exception_handling(self, mock_logger, mock_booster, mock_discovery):
        """Test system stats exception handling."""
        mock_discovery.category_embeddings = None  # Cause AttributeError
        
        result = get_system_stats()
        
        assert "error" in result
        mock_logger.warning.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
