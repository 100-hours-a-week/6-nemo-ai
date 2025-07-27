"""
Unit tests for moderation utilities.
Tests for app/core/moderation.py
"""

import pytest
from typing import Dict, List

# Import from app instead of src
try:
    from app.core.moderation import (
        is_inappropriate_content,
        filter_inappropriate_text,
        check_spam_patterns,
        validate_content_safety
    )
except ImportError:
    pytest.skip("Moderation module not available", allow_module_level=True)


@pytest.mark.unit
class TestModeration:
    """Unit tests for content moderation functions."""

    @pytest.mark.parametrize("text,expected", [
        ("안녕하세요! 좋은 모임 찾고 있어요.", False),
        ("개발 스터디 참여하고 싶습니다.", False),
        ("", False),  # Empty text should not be inappropriate
        ("   ", False),  # Whitespace only should not be inappropriate
    ])
    def test_is_appropriate_content(self, text, expected):
        """Test detection of appropriate content."""
        result = is_inappropriate_content(text)
        assert result == expected

    def test_filter_inappropriate_text_clean_content(self):
        """Test filtering of clean content."""
        clean_texts = [
            "안녕하세요! 개발 스터디 찾고 있어요.",
            "요리 모임에 참여하고 싶습니다.",
            "독서 클럽 추천해주세요.",
            "운동 파트너 구해요."
        ]
        
        for text in clean_texts:
            result = filter_inappropriate_text(text)
            assert result == text  # Should return unchanged

    def test_check_spam_patterns_normal_content(self):
        """Test spam detection on normal content."""
        normal_texts = [
            "개발 스터디 모임 찾아요",
            "주말에 같이 운동하실분",
            "영어 회화 연습 모임",
            "맛집 탐방 모임 참여하고 싶어요"
        ]
        
        for text in normal_texts:
            is_spam = check_spam_patterns(text)
            assert not is_spam

    def test_check_spam_patterns_repetitive_content(self):
        """Test spam detection on repetitive content."""
        spam_texts = [
            "모임모임모임모임모임모임모임모임",
            "!!!!!!!!!!!!!!!!!!!!!!!!",
            "ㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋㅋ",
        ]
        
        for text in spam_texts:
            is_spam = check_spam_patterns(text)
            assert is_spam

    def test_validate_content_safety_comprehensive(self):
        """Test comprehensive content safety validation."""
        test_cases = [
            {
                "text": "안녕하세요! 개발 모임 찾고 있어요.",
                "expected_safe": True,
                "expected_filtered": "안녕하세요! 개발 모임 찾고 있어요."
            },
            {
                "text": "",
                "expected_safe": True,
                "expected_filtered": ""
            },
            {
                "text": "   ",
                "expected_safe": True,
                "expected_filtered": "   "
            }
        ]
        
        for case in test_cases:
            result = validate_content_safety(case["text"])
            
            assert "is_safe" in result
            assert "filtered_text" in result
            assert "warnings" in result
            
            assert result["is_safe"] == case["expected_safe"]
            assert result["filtered_text"] == case["expected_filtered"]
            assert isinstance(result["warnings"], list)

    def test_empty_and_whitespace_handling(self):
        """Test handling of empty and whitespace-only content."""
        edge_cases = ["", "   ", "\n\t\r", None]
        
        for text in edge_cases:
            # Should not crash on edge cases
            try:
                if text is not None:
                    inappropriate = is_inappropriate_content(text)
                    filtered = filter_inappropriate_text(text)
                    spam = check_spam_patterns(text)
                    safety = validate_content_safety(text)
                    
                    # Basic assertions
                    assert isinstance(inappropriate, bool)
                    assert isinstance(filtered, str)
                    assert isinstance(spam, bool)
                    assert isinstance(safety, dict)
                    
            except Exception as e:
                pytest.fail(f"Function should handle edge case '{text}': {e}")

    def test_long_content_handling(self):
        """Test handling of very long content."""
        long_text = "안녕하세요! " * 1000  # Very long text
        
        # Should handle long content without crashing
        inappropriate = is_inappropriate_content(long_text)
        filtered = filter_inappropriate_text(long_text)
        spam = check_spam_patterns(long_text)
        safety = validate_content_safety(long_text)
        
        assert isinstance(inappropriate, bool)
        assert isinstance(filtered, str)
        assert isinstance(spam, bool)
        assert isinstance(safety, dict)

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        special_texts = [
            "안녕하세요! 😊",
            "café 모임",
            "Naïve approach",
            "こんにちは",
            "🎯 목표 달성 모임",
            "특수문자 @#$%^&*()",
        ]
        
        for text in special_texts:
            # Should handle unicode and special characters
            try:
                inappropriate = is_inappropriate_content(text)
                filtered = filter_inappropriate_text(text)
                spam = check_spam_patterns(text)
                
                assert isinstance(inappropriate, bool)
                assert isinstance(filtered, str)
                assert isinstance(spam, bool)
                
            except Exception as e:
                pytest.fail(f"Should handle special text '{text}': {e}")

    def test_mixed_language_content(self):
        """Test handling of mixed language content."""
        mixed_texts = [
            "English and 한국어 mixed",
            "programming 스터디 모임",
            "café 맛집 탐방",
            "Hello 안녕하세요 こんにちは"
        ]
        
        for text in mixed_texts:
            # Should handle mixed languages appropriately
            inappropriate = is_inappropriate_content(text)
            filtered = filter_inappropriate_text(text)
            spam = check_spam_patterns(text)
            
            assert isinstance(inappropriate, bool)
            assert isinstance(filtered, str)
            assert isinstance(spam, bool)
            
            # Mixed language content should generally be considered safe
            assert not inappropriate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
