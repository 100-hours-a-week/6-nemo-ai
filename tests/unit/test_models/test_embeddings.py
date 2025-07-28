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
        assert isinstance(embedding[0], list)  # Should be list of floats
        assert len(embedding[0]) > 0   # Should have dimensions
        
        # Test dimension consistency
        assert len(embedding[0]) == 384  # E5-small has 384 dimensions

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
            assert isinstance(embedding, list)
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
            assert isinstance(embedding, list)
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
            assert isinstance(embedding, list)
            assert len(embedding) == 384

    def test_empty_input_handling(self, embeddings_model):
        """Test handling of empty input."""
        empty_texts = []
        
        embeddings = embeddings_model(empty_texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 0

    def test_global_embed_function(self):
        """Test the global embed function."""
        text = "테스트 텍스트"
        
        embedding = embed([text])
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1
        assert isinstance(embedding[0], list)
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
        
        assert embedding1 == embedding2

    def test_different_inputs_different_embeddings(self, embeddings_model):
        """Test that different inputs produce different embeddings."""
        text1 = "첫 번째 텍스트"
        text2 = "두 번째 텍스트"
        
        embedding1 = embeddings_model([text1])
        embedding2 = embeddings_model([text2])
        
        assert embedding1 != embedding2

    def test_similarity_computation(self, embeddings_model):
        """Test computing similarity between embeddings."""
        similar_texts = ["개발 스터디", "프로그래밍 모임"]
        different_texts = ["개발 스터디", "요리 클래스"]
        
        similar_embeddings = embeddings_model(similar_texts)
        different_embeddings = embeddings_model(different_texts)
        
        # Compute cosine similarity
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        similar_score = cosine_similarity(similar_embeddings[0], similar_embeddings[1])
        different_score = cosine_similarity(different_embeddings[0], different_embeddings[1])
        
        # Similar texts should have higher similarity than different texts
        assert similar_score > different_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
