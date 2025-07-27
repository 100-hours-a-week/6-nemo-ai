"""
Unit tests for embedding models.
Tests for app/models/e5_embeddings.py
"""

import pytest
import numpy as np
from typing import List, Union

# Import from app instead of src
try:
    from app.models.e5_embeddings import (
        E5Embeddings,
        generate_embedding,
        batch_generate_embeddings,
        calculate_similarity
    )
except ImportError:
    pytest.skip("E5 embeddings model not available", allow_module_level=True)


@pytest.mark.unit
class TestE5Embeddings:
    """Unit tests for E5Embeddings model."""

    @pytest.fixture
    def embeddings_model(self):
        """Create an E5Embeddings instance for testing."""
        return E5Embeddings()

    def test_embeddings_model_initialization(self, embeddings_model):
        """Test E5Embeddings model initialization."""
        assert embeddings_model is not None
        assert hasattr(embeddings_model, 'model')
        assert hasattr(embeddings_model, 'tokenizer')

    def test_single_text_embedding(self, embeddings_model):
        """Test generating embedding for single text."""
        text = "안녕하세요! 개발 스터디 모임입니다."
        
        embedding = embeddings_model.encode(text)
        
        # Check embedding properties
        assert isinstance(embedding, (np.ndarray, list))
        if isinstance(embedding, np.ndarray):
            assert embedding.ndim == 1  # Should be 1D vector
            assert len(embedding) > 0   # Should have dimensions

    def test_batch_text_embeddings(self, embeddings_model):
        """Test generating embeddings for multiple texts."""
        texts = [
            "개발 스터디 모임",
            "요리 클래스",
            "운동 동호회",
            "독서 모임"
        ]
        
        embeddings = embeddings_model.encode(texts)
        
        # Check batch embeddings
        assert isinstance(embeddings, (np.ndarray, list))
        if isinstance(embeddings, np.ndarray):
            assert embeddings.ndim == 2  # Should be 2D array
            assert embeddings.shape[0] == len(texts)  # One embedding per text

    def test_korean_text_embedding(self, embeddings_model):
        """Test embedding generation for Korean text."""
        korean_texts = [
            "안녕하세요",
            "개발 스터디",
            "프로그래밍 모임",
            "한국어 자연어 처리"
        ]
        
        for text in korean_texts:
            embedding = embeddings_model.encode(text)
            assert isinstance(embedding, (np.ndarray, list))
            if isinstance(embedding, np.ndarray):
                assert len(embedding) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
