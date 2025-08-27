"""
Unit tests for core/utils.py
Tests utility functions for text processing, validation, and Korean language handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import List

from app.core.utils import (
    is_similar_to_any,
    clean_text,
    validate_non_empty,
    extract_keywords,
    extract_meaningful_terms,
    truncate_text,
    normalize_korean_text,
    contains_korean,
    split_korean_english
)


class TestIsSimilarToAny:
    """Test is_similar_to_any function"""
    
    @patch('app.models.embedding_model.embed')
    @patch('app.core.utils.cosine_similarity')
    def test_similar_text_detection(self, mock_cosine, mock_embed):
        """Test detection of similar text"""
        # Setup mocks
        mock_embed.return_value = [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3], [0.9, 0.8, 0.7]]
        mock_cosine.return_value = [[0.95, 0.3]]  # High similarity with first text
        
        result = is_similar_to_any(
            "새로운 텍스트",
            ["비슷한 텍스트", "다른 텍스트"],
            threshold=0.9
        )
        
        assert result is True
        mock_embed.assert_called_once_with(["비슷한 텍스트", "다른 텍스트", "새로운 텍스트"])
    
    @patch('app.models.embedding_model.embed')
    @patch('app.core.utils.cosine_similarity')
    def test_dissimilar_text_detection(self, mock_cosine, mock_embed):
        """Test detection of dissimilar text"""
        # Setup mocks
        mock_embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.9, 0.8, 0.7]]
        mock_cosine.return_value = [[0.2, 0.3]]  # Low similarity with all texts
        
        result = is_similar_to_any(
            "완전히 다른 텍스트",
            ["기존 텍스트 1", "기존 텍스트 2"],
            threshold=0.9
        )
        
        assert result is False
    
    def test_empty_past_texts(self):
        """Test handling of empty past texts list"""
        result = is_similar_to_any("새로운 텍스트", [], threshold=0.9)
        assert result is False
    
    @patch('app.models.embedding_model.embed')
    def test_embedding_exception_handling(self, mock_embed):
        """Test handling of embedding exceptions"""
        mock_embed.side_effect = Exception("Embedding failed")
        
        result = is_similar_to_any(
            "텍스트",
            ["기존 텍스트"],
            threshold=0.9
        )
        
        assert result is False
    
    @patch('app.models.embedding_model.embed')
    def test_mismatched_vector_count(self, mock_embed):
        """Test handling when vector count doesn't match text count"""
        mock_embed.return_value = [[0.1, 0.2]]  # Only 1 vector for 2 texts
        
        result = is_similar_to_any(
            "텍스트",
            ["기존 텍스트"],
            threshold=0.9
        )
        
        assert result is False


class TestCleanText:
    """Test clean_text function"""
    
    def test_clean_excessive_whitespace(self):
        """Test cleaning excessive whitespace"""
        text = "여러     공백이    있는   텍스트"
        result = clean_text(text)
        assert result == "여러 공백이 있는 텍스트"
    
    def test_clean_leading_trailing_whitespace(self):
        """Test cleaning leading and trailing whitespace"""
        text = "   앞뒤 공백   "
        result = clean_text(text)
        assert result == "앞뒤 공백"
    
    def test_clean_newlines_and_tabs(self):
        """Test cleaning newlines and tabs"""
        text = "줄바꿈\n탭\t문자"
        result = clean_text(text)
        assert result == "줄바꿈 탭 문자"
    
    def test_clean_empty_text(self):
        """Test cleaning empty text"""
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_clean_already_clean_text(self):
        """Test cleaning already clean text"""
        text = "깔끔한 텍스트"
        result = clean_text(text)
        assert result == "깔끔한 텍스트"


class TestValidateNonEmpty:
    """Test validate_non_empty function"""
    
    def test_validate_valid_text(self):
        """Test validation of valid text"""
        result = validate_non_empty("유효한 텍스트", "test_field")
        assert result == "유효한 텍스트"
    
    def test_validate_text_with_whitespace(self):
        """Test validation strips whitespace"""
        result = validate_non_empty("  공백이 있는 텍스트  ", "test_field")
        assert result == "공백이 있는 텍스트"
    
    def test_validate_empty_text_raises_error(self):
        """Test validation raises error for empty text"""
        with pytest.raises(ValueError) as exc_info:
            validate_non_empty("", "test_field")
        assert "test_field cannot be empty" in str(exc_info.value)
    
    def test_validate_whitespace_only_raises_error(self):
        """Test validation raises error for whitespace-only text"""
        with pytest.raises(ValueError) as exc_info:
            validate_non_empty("   ", "test_field")
        assert "test_field cannot be empty" in str(exc_info.value)
    
    def test_validate_none_raises_error(self):
        """Test validation raises error for None"""
        with pytest.raises(ValueError) as exc_info:
            validate_non_empty(None, "test_field")
        assert "test_field cannot be empty" in str(exc_info.value)


class TestExtractKeywords:
    """Test extract_keywords function"""
    
    def test_extract_korean_keywords(self):
        """Test extracting Korean keywords"""
        text = "파이썬 프로그래밍 스터디 모임에서 웹 개발을 배웁니다"
        result = extract_keywords(text)
        
        # Should extract meaningful Korean words (the function extracts complete words, not particles)
        assert "파이썬" in result
        assert "프로그래밍" in result
        assert "스터디" in result
        assert "모임에서" in result  # Function extracts complete word with particle
        assert "개발을" in result  # Function extracts complete word with particle
        assert "배웁니다" in result
        
        # Single character words like "웹" are filtered out (len(word) > 1 requirement)
        assert "웹" not in result
        
        # Should exclude stopwords that are standalone
        assert "에서" not in result  # standalone particles are excluded
        assert "을" not in result   # standalone particles are excluded
    
    def test_extract_english_keywords(self):
        """Test extracting English keywords"""
        text = "Python programming study group for web development"
        result = extract_keywords(text)
        
        # Should extract meaningful English words
        assert "python" in result
        assert "programming" in result
        assert "study" in result
        assert "group" in result
        assert "web" in result
        assert "development" in result
        
        # Should exclude stopwords
        assert "for" not in result
    
    def test_extract_mixed_language_keywords(self):
        """Test extracting keywords from mixed Korean-English text"""
        text = "Python 파이썬 programming 프로그래밍 study"
        result = extract_keywords(text)
        
        assert "python" in result
        assert "파이썬" in result
        assert "programming" in result
        assert "프로그래밍" in result
        assert "study" in result
    
    def test_extract_keywords_max_limit(self):
        """Test keyword extraction respects max limit"""
        text = "하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉 열 열하나 열둘"
        result = extract_keywords(text, max_keywords=5)
        
        assert len(result) == 5
    
    def test_extract_keywords_removes_duplicates(self):
        """Test keyword extraction removes duplicates"""
        text = "파이썬 파이썬 프로그래밍 파이썬 스터디"
        result = extract_keywords(text)
        
        # Should only have unique keywords
        assert result.count("파이썬") == 1
    
    def test_extract_keywords_empty_text(self):
        """Test keyword extraction from empty text"""
        assert extract_keywords("") == []
        assert extract_keywords(None) == []
    
    def test_extract_keywords_punctuation_removal(self):
        """Test that punctuation is removed"""
        text = "파이썬! 프로그래밍? 스터디..."
        result = extract_keywords(text)
        
        assert "파이썬" in result
        assert "프로그래밍" in result
        assert "스터디" in result


class TestExtractMeaningfulTerms:
    """Test extract_meaningful_terms function"""
    
    def test_extract_meaningful_korean_terms(self):
        """Test extracting meaningful Korean terms"""
        text = "파이썬을 배우는 스터디 모임입니다"
        result = extract_meaningful_terms(text)
        
        # The function extracts complete words as they appear, including particles
        assert "파이썬을" in result  # Complete word with particle
        assert "배우는" in result
        assert "스터디" in result
        assert "모임입니다" in result  # Complete word with ending
        
        # Should exclude standalone stopwords but "을" as part of "파이썬을" is included
    
    def test_extract_meaningful_terms_filters_short_words(self):
        """Test that short words are filtered out"""
        text = "긴 단어와 짧은 단어들 중에서 의미있는 것만"
        result = extract_meaningful_terms(text)
        
        # Single character words should be excluded
        assert all(len(term) > 1 for term in result)
    
    def test_extract_meaningful_terms_empty_text(self):
        """Test with empty text"""
        assert extract_meaningful_terms("") == []
        assert extract_meaningful_terms(None) == []


class TestTruncateText:
    """Test truncate_text function"""
    
    def test_truncate_long_text(self):
        """Test truncating text that exceeds max length"""
        text = "매우 " * 100 + "긴 텍스트"
        result = truncate_text(text, max_length=50)
        
        assert len(result) == 50
        assert result.endswith("...")
    
    def test_truncate_short_text_unchanged(self):
        """Test that short text remains unchanged"""
        text = "짧은 텍스트"
        result = truncate_text(text, max_length=100)
        
        assert result == text
    
    def test_truncate_custom_suffix(self):
        """Test truncation with custom suffix"""
        text = "매우 " * 50 + "긴 텍스트"
        result = truncate_text(text, max_length=20, suffix="[더보기]")
        
        assert len(result) == 20
        assert result.endswith("[더보기]")
    
    def test_truncate_empty_text(self):
        """Test truncating empty text"""
        assert truncate_text("", max_length=50) == ""
        assert truncate_text(None, max_length=50) is None  # Function returns None for None input


class TestNormalizeKoreanText:
    """Test normalize_korean_text function"""
    
    def test_normalize_excessive_whitespace(self):
        """Test normalizing excessive whitespace"""
        text = "여러     공백이    있는   텍스트"
        result = normalize_korean_text(text)
        assert result == "여러 공백이 있는 텍스트"
    
    def test_normalize_repeated_punctuation(self):
        """Test normalizing repeated punctuation"""
        text = "정말!!! 좋아요??? 그래서.......끝"
        result = normalize_korean_text(text)
        assert result == "정말! 좋아요? 그래서...끝"
    
    def test_normalize_empty_text(self):
        """Test normalizing empty text"""
        assert normalize_korean_text("") == ""
        assert normalize_korean_text(None) == ""


class TestContainsKorean:
    """Test contains_korean function"""
    
    def test_text_with_korean(self):
        """Test text containing Korean characters"""
        assert contains_korean("한글이 포함된 텍스트") is True
        assert contains_korean("Mixed 한글 English") is True
        assert contains_korean("안녕하세요") is True
    
    def test_text_without_korean(self):
        """Test text without Korean characters"""
        assert contains_korean("Only English text") is False
        assert contains_korean("123456") is False
        assert contains_korean("!@#$%") is False
    
    def test_empty_text(self):
        """Test empty text"""
        assert contains_korean("") is False
        assert contains_korean(None) is False


class TestSplitKoreanEnglish:
    """Test split_korean_english function"""
    
    def test_split_mixed_text(self):
        """Test splitting mixed Korean-English text"""
        text = "Python 파이썬 programming 프로그래밍 study 스터디"
        korean_words, english_words = split_korean_english(text)
        
        assert "파이썬" in korean_words
        assert "프로그래밍" in korean_words
        assert "스터디" in korean_words
        
        assert "python" in english_words
        assert "programming" in english_words
        assert "study" in english_words
    
    def test_split_korean_only_text(self):
        """Test splitting Korean-only text"""
        text = "파이썬 프로그래밍 스터디"
        korean_words, english_words = split_korean_english(text)
        
        assert len(korean_words) == 3
        assert len(english_words) == 0
    
    def test_split_english_only_text(self):
        """Test splitting English-only text"""
        text = "Python programming study"
        korean_words, english_words = split_korean_english(text)
        
        assert len(korean_words) == 0
        assert len(english_words) == 3
    
    def test_split_empty_text(self):
        """Test splitting empty text"""
        korean_words, english_words = split_korean_english("")
        assert korean_words == []
        assert english_words == []
        
        korean_words, english_words = split_korean_english(None)
        assert korean_words == []
        assert english_words == []


if __name__ == "__main__":
    pytest.main([__file__])
