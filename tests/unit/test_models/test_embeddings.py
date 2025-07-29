"""
Unit tests for embedding models.
Tests for app/models/e5_embeddings.py
"""

import pytest
import numpy as np
from typing import List, Union

# Import from app instead of src
try:
    from app.models.e5_embeddings import E5EmbeddingFunction, embed
except ImportError:
    pytest.skip("E5 embeddings model not available", allow_module_level=True)


@pytest.mark.unit
class TestE5Embeddings:
    """Unit tests for E5Embeddings model."""

    @pytest.fixture
    def embeddings_model(self):
        """Create an E5EmbeddingFunction instance for testing."""
        return E5EmbeddingFunction()

    def test_embeddings_model_initialization(self, embeddings_model):
        """Test E5EmbeddingFunction model initialization."""
        assert embeddings_model is not None
        assert hasattr(embeddings_model, 'model')
        assert hasattr(embeddings_model, '_model_name')
        assert hasattr(embeddings_model, 'device')
        assert embeddings_model.device == "cpu"

    def test_single_text_embedding(self, embeddings_model):
        """Test generating embedding for single text."""
        text = "안녕하세요! 개발 스터디 모임입니다."
        
        embedding = embeddings_model([text])
        
        # Check embedding properties
        assert isinstance(embedding, list)
        assert len(embedding) == 1  # Should return one embedding
        
        # ChromaDB returns numpy arrays, so check for that
        assert isinstance(embedding[0], (list, np.ndarray))  # Should be list or numpy array
        assert len(embedding[0]) > 0   # Should have dimensions
        
        # Get actual dimension and verify it's reasonable for E5
        actual_dim = len(embedding[0])
        assert actual_dim == 384  # E5-small has 384 dimensions
        
        # Check that all values are numeric (float or numpy float)
        if isinstance(embedding[0], np.ndarray):
            assert embedding[0].dtype in [np.float32, np.float64]
        else:
            assert all(isinstance(val, (float, int)) for val in embedding[0])

    def test_batch_text_embeddings(self, embeddings_model):
        """Test generating embeddings for multiple texts."""
        texts = [
            "개발 스터디 모임",
            "요리 클래스",
            "운동 동호회",
            "독서 모임"
        ]
        
        embeddings = embeddings_model(texts)
        
        # Check batch embeddings
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)  # One embedding per text
        
        for embedding in embeddings:
            assert isinstance(embedding, (list, np.ndarray))
            assert len(embedding) == 384  # Consistent dimensions

    def test_korean_text_embedding(self, embeddings_model):
        """Test embedding generation for Korean text."""
        korean_texts = [
            "안녕하세요",
            "개발 스터디",
            "프로그래밍 모임",
            "한국어 자연어 처리"
        ]
        
        embeddings = embeddings_model(korean_texts)
        
        assert len(embeddings) == len(korean_texts)
        
        for embedding in embeddings:
            assert isinstance(embedding, (list, np.ndarray))
            assert len(embedding) == 384

    def test_english_text_embedding(self, embeddings_model):
        """Test embedding generation for English text."""
        english_texts = [
            "Hello world",
            "Programming study group",
            "Machine learning",
            "Natural language processing"
        ]
        
        embeddings = embeddings_model(english_texts)
        
        assert len(embeddings) == len(english_texts)
        
        for embedding in embeddings:
            assert isinstance(embedding, (list, np.ndarray))
            assert len(embedding) == 384

    def test_empty_input_handling(self, embeddings_model):
        """Test handling of empty input."""
        empty_texts = []
        
        # ChromaDB's EmbeddingFunction raises an error for empty inputs
        # This is actually the correct behavior for ChromaDB
        with pytest.raises(ValueError, match="Expected Embeddings to be non-empty"):
            embeddings_model(empty_texts)

    def test_global_embed_function(self):
        """Test the global embed function."""
        text = "테스트 텍스트"
        
        embedding = embed([text])
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1
        assert isinstance(embedding[0], (list, np.ndarray))
        assert len(embedding[0]) == 384

    def test_model_name(self, embeddings_model):
        """Test model name retrieval."""
        name = embeddings_model.name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_embedding_consistency(self, embeddings_model):
        """Test that same input produces same embedding."""
        text = "일관성 테스트"
        
        embedding1 = embeddings_model([text])
        embedding2 = embeddings_model([text])
        
        # Convert to numpy arrays for proper comparison
        emb1_array = np.array(embedding1[0])
        emb2_array = np.array(embedding2[0])
        
        # Use numpy.allclose for floating point comparison
        assert np.allclose(emb1_array, emb2_array, rtol=1e-9, atol=1e-9)

    def test_different_inputs_different_embeddings(self, embeddings_model):
        """Test that different inputs produce different embeddings."""
        text1 = "첫 번째 텍스트"
        text2 = "두 번째 텍스트"
        
        embedding1 = embeddings_model([text1])
        embedding2 = embeddings_model([text2])
        
        # Convert to numpy arrays for proper comparison
        emb1_array = np.array(embedding1[0])
        emb2_array = np.array(embedding2[0])
        
        # Use numpy.allclose with NOT to check they are different
        assert not np.allclose(emb1_array, emb2_array, rtol=1e-5, atol=1e-5)

    def test_similarity_computation(self, embeddings_model):
        """Test computing similarity between embeddings."""
        similar_texts = ["개발 스터디", "프로그래밍 모임"]
        different_texts = ["개발 스터디", "요리 클래스"]
        
        similar_embeddings = embeddings_model(similar_texts)
        different_embeddings = embeddings_model(different_texts)
        
        # Compute cosine similarity
        def cosine_similarity(a, b):
            a_array = np.array(a)
            b_array = np.array(b)
            return np.dot(a_array, b_array) / (np.linalg.norm(a_array) * np.linalg.norm(b_array))
        
        similar_score = cosine_similarity(similar_embeddings[0], similar_embeddings[1])
        different_score = cosine_similarity(different_embeddings[0], different_embeddings[1])
        
        # Similar texts should have higher similarity than different texts
        assert similar_score > different_score

    def test_string_input_conversion(self, embeddings_model):
        """Test that string input is properly converted to list."""
        text = "단일 문자열 입력"
        
        # Test both string and list input give same result
        embedding_from_string = embeddings_model(text)
        embedding_from_list = embeddings_model([text])
        
        assert len(embedding_from_string) == 1
        assert len(embedding_from_list) == 1
        
        # Convert to numpy arrays for comparison
        emb1_array = np.array(embedding_from_string[0])
        emb2_array = np.array(embedding_from_list[0])
        
        assert np.allclose(emb1_array, emb2_array, rtol=1e-9, atol=1e-9)

    def test_invalid_input_type(self, embeddings_model):
        """Test handling of invalid input types."""
        with pytest.raises(ValueError, match="입력은 문자열 또는 문자열 리스트여야 합니다"):
            embeddings_model(123)  # Invalid input type
        
        with pytest.raises(ValueError, match="입력은 문자열 또는 문자열 리스트여야 합니다"):
            embeddings_model(None)  # None input

    def test_prefix_addition(self, embeddings_model):
        """Test that E5 models correctly add passage prefix."""
        # This is more of an implementation detail test
        # but important for E5 model performance
        text = "개발 스터디"
        
        embedding = embeddings_model([text])
        
        # Should return valid embedding regardless of prefix logic
        assert isinstance(embedding, list)
        assert len(embedding) == 1
        assert len(embedding[0]) == 384

    def test_multilingual_capability(self, embeddings_model):
        """Test multilingual embedding capability."""
        multilingual_texts = [
            "Hello world",           # English
            "안녕하세요",            # Korean  
            "こんにちは",            # Japanese
            "Bonjour le monde",     # French
            "Hola mundo"            # Spanish
        ]
        
        embeddings = embeddings_model(multilingual_texts)
        
        # All should produce valid embeddings
        assert len(embeddings) == len(multilingual_texts)
        for embedding in embeddings:
            assert isinstance(embedding, (list, np.ndarray))
            assert len(embedding) == 384
            
        # Different languages should produce different embeddings
        english_emb = np.array(embeddings[0])
        korean_emb = np.array(embeddings[1])
        
        # Should be different but both valid
        assert not np.allclose(english_emb, korean_emb, rtol=1e-3)

    def test_embedding_vector_properties(self, embeddings_model):
        """Test mathematical properties of embedding vectors."""
        text = "벡터 속성 테스트"
        
        embedding = embeddings_model([text])
        vector = np.array(embedding[0])
        
        # Check basic vector properties
        assert len(vector) == 384
        assert not np.isnan(vector).any()  # No NaN values
        assert not np.isinf(vector).any()  # No infinite values
        assert vector.dtype in [np.float32, np.float64]  # Proper numeric type
        
        # Embedding should have reasonable magnitude (not all zeros)
        magnitude = np.linalg.norm(vector)
        assert magnitude > 0.1  # Should have substantial magnitude


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
