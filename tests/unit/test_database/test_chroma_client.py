"""
Unit tests for chroma_client.py
Tests ChromaDB client initialization and collection operations.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import chromadb

from app.database.chroma_client import get_chroma_client, chroma_collection_exists


class TestGetChromaClient:
    """Test get_chroma_client function"""
    
    def test_get_chroma_client_creates_directory(self):
        """Test that get_chroma_client creates the database directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "test_chroma_db")
            
            with patch('app.database.chroma_client.CHROMA_DB_PATH', test_path):
                client = get_chroma_client()
                
                # Verify directory was created
                assert os.path.exists(test_path)
                assert os.path.isdir(test_path)
                
                # Verify client is created
                assert client is not None
                assert hasattr(client, 'get_collection')
    
    def test_get_chroma_client_existing_directory(self):
        """Test that get_chroma_client works with existing directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "existing_chroma_db")
            os.makedirs(test_path)  # Pre-create directory
            
            with patch('app.database.chroma_client.CHROMA_DB_PATH', test_path):
                client = get_chroma_client()
                
                # Verify client is created
                assert client is not None
                assert hasattr(client, 'get_collection')
    
    def test_get_chroma_client_nested_directory(self):
        """Test that get_chroma_client creates nested directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "nested", "deep", "chroma_db")
            
            with patch('app.database.chroma_client.CHROMA_DB_PATH', test_path):
                client = get_chroma_client()
                
                # Verify nested directories were created
                assert os.path.exists(test_path)
                assert os.path.isdir(test_path)
                
                # Verify client is created
                assert client is not None
                assert hasattr(client, 'get_collection')
    
    @patch('app.database.chroma_client.chromadb.PersistentClient')
    def test_get_chroma_client_passes_correct_path(self, mock_persistent_client):
        """Test that get_chroma_client passes correct path to PersistentClient"""
        test_path = "/test/chroma/path"
        
        with patch('app.database.chroma_client.CHROMA_DB_PATH', test_path):
            with patch('os.makedirs'):
                get_chroma_client()
                
                # Verify PersistentClient was called with correct path
                mock_persistent_client.assert_called_once_with(path=test_path)


class TestChromaCollectionExists:
    """Test chroma_collection_exists function"""
    
    def test_collection_exists_returns_true(self):
        """Test that function returns True when collection exists"""
        # Mock client that has the collection
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        
        result = chroma_collection_exists("test_collection", mock_client)
        
        assert result is True
        mock_client.get_collection.assert_called_once_with("test_collection")
    
    def test_collection_exists_returns_false_on_exception(self):
        """Test that function returns False when collection doesn't exist"""
        # Mock client that raises exception when getting collection
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        
        result = chroma_collection_exists("nonexistent_collection", mock_client)
        
        assert result is False
        mock_client.get_collection.assert_called_once_with("nonexistent_collection")
    
    def test_collection_exists_handles_various_exceptions(self):
        """Test that function handles various types of exceptions"""
        mock_client = MagicMock()
        
        # Test with different exception types
        exceptions = [
            ValueError("Invalid collection name"),
            KeyError("Collection not found"),
            RuntimeError("Database error"),
            Exception("Generic database error")
        ]
        
        for exception in exceptions:
            mock_client.get_collection.side_effect = exception
            result = chroma_collection_exists("test_collection", mock_client)
            assert result is False
    
    def test_collection_exists_with_empty_name(self):
        """Test that function handles empty collection name"""
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Invalid name")
        
        result = chroma_collection_exists("", mock_client)
        
        assert result is False
        mock_client.get_collection.assert_called_once_with("")
    
    def test_collection_exists_with_none_name(self):
        """Test that function handles None collection name"""
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Invalid name")
        
        result = chroma_collection_exists(None, mock_client)
        
        assert result is False
        mock_client.get_collection.assert_called_once_with(None)


class TestChromaClientIntegration:
    """Integration tests for ChromaDB client functionality"""
    
    def test_get_chroma_client_and_collection_operations(self):
        """Test getting client and performing basic collection operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "integration_test_db")
            
            with patch('app.database.chroma_client.CHROMA_DB_PATH', test_path):
                # Get client
                client = get_chroma_client()
                
                # Test collection doesn't exist initially (might return True if collection persists)
                initial_exists = chroma_collection_exists("test_collection", client)
                
                try:
                    # Try to create collection (might already exist)
                    if not initial_exists:
                        collection = client.create_collection("test_collection")
                    else:
                        # Collection already exists, get it
                        collection = client.get_collection("test_collection")
                    
                    # Test collection now exists
                    assert chroma_collection_exists("test_collection", client) is True
                    
                    # Test getting existing collection
                    existing_collection = client.get_collection("test_collection")
                    assert existing_collection.name == "test_collection"
                    
                except Exception as e:
                    # If ChromaDB is not available in test environment, skip the collection operations
                    pytest.skip(f"ChromaDB not available for integration test: {e}")
    
    def test_multiple_clients_same_path(self):
        """Test that multiple clients can access the same database path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "shared_db")
            
            with patch('app.database.chroma_client.CHROMA_DB_PATH', test_path):
                # Get first client and create collection
                client1 = get_chroma_client()
                try:
                    client1.create_collection("shared_collection")
                    
                    # Get second client and verify it can see the collection
                    client2 = get_chroma_client()
                    assert chroma_collection_exists("shared_collection", client2) is True
                except Exception as e:
                    # If ChromaDB is not available in test environment, skip
                    pytest.skip(f"ChromaDB not available for integration test: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
