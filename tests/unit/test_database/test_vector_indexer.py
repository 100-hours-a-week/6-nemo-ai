"""
Unit tests for vector_indexer.py
Tests document indexing functionality for ChromaDB vector database.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from app.database.vector_indexer import add_documents_to_vector_db, GROUP_COLLECTION, USER_COLLECTION, SYN_COLLECTION


class TestAddDocumentsToVectorDb:
    """Test add_documents_to_vector_db function"""
    
    def setup_method(self):
        """Setup test data"""
        self.sample_docs = [
            {
                "id": "doc-1",
                "text": "첫 번째 테스트 문서입니다.",
                "metadata": {
                    "groupId": "group-1",
                    "name": "테스트 모임 1",
                    "tags": "테스트, 모임"
                }
            },
            {
                "id": "doc-2", 
                "text": "두 번째 테스트 문서입니다.",
                "metadata": {
                    "groupId": "group-2",
                    "name": "테스트 모임 2",
                    "tags": "테스트, 개발"
                }
            }
        ]
    
    @patch('app.database.vector_indexer.get_chroma_client')
    @patch('app.database.vector_indexer.embed')
    def test_add_documents_new_collection(self, mock_embed, mock_get_client):
        """Test adding documents to a new collection"""
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_collections.return_value = []  # No existing collections
        
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        mock_embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]  # Mock embeddings
        
        # Execute
        add_documents_to_vector_db(self.sample_docs, GROUP_COLLECTION)
        
        # Verify
        mock_get_client.assert_called_once()
        mock_client.list_collections.assert_called_once()
        mock_client.get_or_create_collection.assert_called_once_with(
            name=GROUP_COLLECTION, 
            embedding_function=mock_embed
        )
        
        # Verify embedding was called with texts
        mock_embed.assert_called_with([
            "첫 번째 테스트 문서입니다.",
            "두 번째 테스트 문서입니다."
        ])
        
        # Verify collection operations
        mock_collection.delete.assert_called_once_with(ids=["doc-1", "doc-2"])
        mock_collection.add.assert_called_once_with(
            ids=["doc-1", "doc-2"],
            documents=["첫 번째 테스트 문서입니다.", "두 번째 테스트 문서입니다."],
            metadatas=[
                {"groupId": "group-1", "name": "테스트 모임 1", "tags": "테스트, 모임"},
                {"groupId": "group-2", "name": "테스트 모임 2", "tags": "테스트, 개발"}
            ],
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
    
    @patch('app.database.vector_indexer.get_chroma_client')
    @patch('app.database.vector_indexer.embed')
    def test_add_documents_existing_collection(self, mock_embed, mock_get_client):
        """Test adding documents to an existing collection"""
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock existing collection
        mock_existing_collection = MagicMock()
        mock_existing_collection.name = GROUP_COLLECTION
        mock_client.list_collections.return_value = [mock_existing_collection]
        
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        
        mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        # Execute
        add_documents_to_vector_db(self.sample_docs, GROUP_COLLECTION)
        
        # Verify existing collection is used
        mock_client.get_collection.assert_called_once_with(name=GROUP_COLLECTION)
        mock_client.get_or_create_collection.assert_not_called()
        
        # Verify documents are added
        mock_collection.add.assert_called_once()
    
    @patch('app.database.vector_indexer.get_chroma_client')
    def test_add_documents_empty_list(self, mock_get_client):
        """Test adding empty document list"""
        # Execute
        add_documents_to_vector_db([], GROUP_COLLECTION)
        
        # Verify no client operations are performed
        mock_get_client.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
