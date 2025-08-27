"""
Unit tests for retry_handler.py
Tests ContentValidator and RetryHandler classes for AI-generated content validation and retry logic.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import List, Tuple, Any

from app.services.shared.retry_handler import ContentValidator, RetryHandler


class TestContentValidator:
    """Test ContentValidator class functionality"""

    def test_is_empty_or_invalid_with_empty_strings(self):
        """Test empty string detection"""
        assert ContentValidator.is_empty_or_invalid("")
        assert ContentValidator.is_empty_or_invalid("   ")
        assert ContentValidator.is_empty_or_invalid(None)
        assert ContentValidator.is_empty_or_invalid("ab")  # Too short
        
    def test_is_empty_or_invalid_with_valid_strings(self):
        """Test valid string detection"""
        assert not ContentValidator.is_empty_or_invalid("Valid meeting name")
        assert not ContentValidator.is_empty_or_invalid("string")  # Valid meeting name
        assert not ContentValidator.is_empty_or_invalid("Test description")
        
    def test_is_empty_or_invalid_with_placeholder_values(self):
        """Test placeholder value detection"""
        assert ContentValidator.is_empty_or_invalid("none")
        assert ContentValidator.is_empty_or_invalid("NULL")
        assert ContentValidator.is_empty_or_invalid("undefined")
        
    def test_contains_pii_with_phone_numbers(self):
        """Test PII detection for phone numbers"""
        assert ContentValidator.contains_pii("연락처: 010-1234-5678")
        assert ContentValidator.contains_pii("문의: 02-123-4567")
        assert not ContentValidator.contains_pii("모임 시간: 10시-12시")
        
    def test_contains_pii_with_email_addresses(self):
        """Test PII detection for email addresses"""
        assert ContentValidator.contains_pii("문의: test@example.com")
        assert ContentValidator.contains_pii("Contact user.name@domain.org")
        assert not ContentValidator.contains_pii("이메일로 안내 예정")
        
    def test_contains_pii_with_urls(self):
        """Test PII detection for URLs"""
        assert ContentValidator.contains_pii("참고: https://example.com")
        assert ContentValidator.contains_pii("사이트: http://test.org")
        assert not ContentValidator.contains_pii("웹사이트 제작 예정")
        
    def test_contains_pii_with_money_amounts(self):
        """Test PII detection for money amounts"""
        assert ContentValidator.contains_pii("참가비: 50,000원")
        assert ContentValidator.contains_pii("비용: 10000원")
        assert not ContentValidator.contains_pii("원하는 목표 달성")
        
    def test_contains_pii_with_dates_and_times(self):
        """Test PII detection for dates and times"""
        assert ContentValidator.contains_pii("일시: 2024.12.25")
        assert ContentValidator.contains_pii("시간: 14:30")
        assert not ContentValidator.contains_pii("12월 모임 예정")
        
    def test_contains_irrelevant_content_with_construction_terms(self):
        """Test irrelevant content detection for construction-related terms"""
        # Should be irrelevant when topic is not construction
        assert ContentValidator.contains_irrelevant_content(
            "한국건설기술인협회에서 주관하는 프로젝트", 
            "프로그래밍"
        )
        assert ContentValidator.contains_irrelevant_content(
            "건설워크넷 담당자 문의", 
            "요리"
        )
        
        # Should not be irrelevant when topic is construction
        assert not ContentValidator.contains_irrelevant_content(
            "건설 분야 전문가 모임", 
            "건설업"
        )
        
    def test_clean_content_removes_pii(self):
        """Test content cleaning removes PII"""
        text = "문의: 010-1234-5678, 이메일: test@example.com"
        cleaned = ContentValidator.clean_content(text)
        assert "010-1234-5678" not in cleaned
        assert "test@example.com" not in cleaned
        assert "[정보삭제]" in cleaned
        
    def test_clean_content_removes_irrelevant_sentences(self):
        """Test content cleaning removes irrelevant sentences"""
        text = "프로그래밍 스터디입니다. 한국건설기술인협회에서 진행합니다. 파이썬을 배웁니다."
        cleaned = ContentValidator.clean_content(text, "프로그래밍")
        assert "한국건설기술인협회" not in cleaned
        assert "프로그래밍 스터디입니다" in cleaned
        assert "파이썬을 배웁니다" in cleaned
        
    def test_clean_content_normalizes_whitespace(self):
        """Test content cleaning normalizes whitespace"""
        text = "여러     공백이    있는   텍스트"
        cleaned = ContentValidator.clean_content(text)
        assert "여러 공백이 있는 텍스트" == cleaned
        
    def test_validate_meeting_data_with_valid_data(self):
        """Test meeting data validation with valid data"""
        is_valid, issues = ContentValidator.validate_meeting_data(
            name="파이썬 스터디",
            summary="파이썬 프로그래밍을 배우는 스터디 모임입니다.",
            description="매주 파이썬 기초부터 심화까지 학습하며 프로젝트를 진행합니다.",
            tags=["파이썬", "프로그래밍", "스터디"],
            topic_context="프로그래밍"
        )
        assert is_valid
        assert len(issues) == 0
        
    def test_validate_meeting_data_with_empty_fields(self):
        """Test meeting data validation with empty fields"""
        is_valid, issues = ContentValidator.validate_meeting_data(
            name="",
            summary="",
            description="",
            tags=[],
            topic_context=""
        )
        assert not is_valid
        assert "Name is empty or invalid" in issues
        assert "Summary is empty or invalid" in issues
        assert "Description is empty or invalid" in issues
        assert "Tags list is empty" in issues
        
    def test_validate_meeting_data_with_pii(self):
        """Test meeting data validation with PII"""
        is_valid, issues = ContentValidator.validate_meeting_data(
            name="파이썬 스터디",
            summary="연락처: 010-1234-5678로 문의해주세요.",
            description="이메일 test@example.com으로 가입하세요.",
            tags=["파이썬", "010-9999-8888"],  # Simple phone number pattern
            topic_context="프로그래밍"
        )
        assert not is_valid
        # Check that at least some PII was detected (could be 1-3 depending on what's detected)
        pii_issues = [issue for issue in issues if "PII" in issue]
        assert len(pii_issues) >= 1  # Should detect at least one PII instance
        
    def test_validate_meeting_data_with_short_content(self):
        """Test meeting data validation with too short content"""
        is_valid, issues = ContentValidator.validate_meeting_data(
            name="파이썬 스터디",
            summary="짧음",
            description="너무 짧은 설명",
            tags=["파이썬"],
            topic_context="프로그래밍"
        )
        assert not is_valid
        assert "Summary too short" in issues
        assert "Description too short" in issues
        
    def test_validate_meeting_data_with_long_content(self):
        """Test meeting data validation with too long content"""
        # Create content that's definitely over the limits
        # "매우 " is 3 chars, so need 70+ repetitions for 200+ chars
        long_summary = "매우 " * 70 + "긴 요약입니다."  # Should be over 200 chars
        # Need 350+ repetitions for 1000+ chars  
        long_description = "매우 " * 350 + "긴 설명입니다."  # Should be over 1000 chars
        
        # Verify our test data is actually long enough
        assert len(long_summary) > 200, f"Summary length {len(long_summary)} not > 200"
        assert len(long_description) > 1000, f"Description length {len(long_description)} not > 1000"
        
        is_valid, issues = ContentValidator.validate_meeting_data(
            name="파이썬 스터디",
            summary=long_summary,
            description=long_description,
            tags=["파이썬"],
            topic_context="프로그래밍"
        )
        assert not is_valid
        assert "Summary too long" in issues
        assert "Description too long" in issues
        
    def test_validate_meeting_data_with_irrelevant_content(self):
        """Test meeting data validation with irrelevant content"""
        is_valid, issues = ContentValidator.validate_meeting_data(
            name="파이썬 스터디",
            summary="파이썬을 배우는 스터디입니다. 한국건설기술인협회에서 주관합니다.",
            description="프로그래밍을 배우는 모임입니다. 건설워크넷 담당자에게 문의하세요.",
            tags=["파이썬", "한국건설기술인협회"],
            topic_context="프로그래밍"
        )
        assert not is_valid
        assert "Summary contains irrelevant content" in issues
        assert "Description contains irrelevant content" in issues
        assert "Tag contains irrelevant content: 한국건설기술인협회" in issues


class TestRetryHandler:
    """Test RetryHandler class functionality"""
    
    def test_init_with_default_values(self):
        """Test RetryHandler initialization with default values"""
        handler = RetryHandler()
        assert handler.max_retries == 3
        assert handler.base_delay == 1.0
        
    def test_init_with_custom_values(self):
        """Test RetryHandler initialization with custom values"""
        handler = RetryHandler(max_retries=5, base_delay=0.5)
        assert handler.max_retries == 5
        assert handler.base_delay == 0.5
        
    @pytest.mark.asyncio
    async def test_retry_with_validation_success_first_try(self):
        """Test successful operation on first try"""
        handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        # Mock operation that succeeds
        operation = AsyncMock(return_value="success")
        
        # Mock validator that passes
        validator = MagicMock(return_value=(True, []))
        
        result = await handler.retry_with_validation(
            operation, validator, "test_operation"
        )
        
        assert result == "success"
        operation.assert_called_once()
        validator.assert_called_once_with("success")
        
    @pytest.mark.asyncio
    async def test_retry_with_validation_success_after_retries(self):
        """Test successful operation after validation failures"""
        handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        # Mock operation that always succeeds
        operation = AsyncMock(return_value="success")
        
        # Mock validator that fails first two times, then succeeds
        validator = MagicMock(side_effect=[
            (False, ["validation error 1"]),
            (False, ["validation error 2"]),
            (True, [])
        ])
        
        result = await handler.retry_with_validation(
            operation, validator, "test_operation"
        )
        
        assert result == "success"
        assert operation.call_count == 3
        assert validator.call_count == 3
        
    @pytest.mark.asyncio
    async def test_retry_with_validation_operation_exception_then_success(self):
        """Test operation exception followed by success"""
        handler = RetryHandler(max_retries=3, base_delay=0.1)
        
        # Mock operation that fails first time, succeeds second time
        operation = AsyncMock(side_effect=[
            Exception("operation failed"),
            "success"
        ])
        
        # Mock validator that passes
        validator = MagicMock(return_value=(True, []))
        
        result = await handler.retry_with_validation(
            operation, validator, "test_operation"
        )
        
        assert result == "success"
        assert operation.call_count == 2
        validator.assert_called_once_with("success")
        
    @pytest.mark.asyncio
    async def test_retry_with_validation_all_attempts_fail_validation(self):
        """Test all attempts fail validation"""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        # Mock operation that always succeeds
        operation = AsyncMock(return_value="invalid_result")
        
        # Mock validator that always fails
        validator = MagicMock(return_value=(False, ["validation failed"]))
        
        with pytest.raises(Exception) as exc_info:
            await handler.retry_with_validation(
                operation, validator, "test_operation"
            )
            
        assert "All 2 attempts failed for test_operation" in str(exc_info.value)
        assert "validation failed" in str(exc_info.value)
        assert operation.call_count == 2
        assert validator.call_count == 2
        
    @pytest.mark.asyncio
    async def test_retry_with_validation_all_attempts_fail_exception(self):
        """Test all attempts fail with exceptions"""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        # Mock operation that always fails
        operation = AsyncMock(side_effect=Exception("operation failed"))
        
        # Mock validator (should not be called)
        validator = MagicMock()
        
        with pytest.raises(Exception) as exc_info:
            await handler.retry_with_validation(
                operation, validator, "test_operation"
            )
            
        assert "All 2 attempts failed for test_operation" in str(exc_info.value)
        assert "operation failed" in str(exc_info.value)
        assert operation.call_count == 2
        validator.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_retry_with_validation_mixed_failures(self):
        """Test mixed exception and validation failures"""
        handler = RetryHandler(max_retries=4, base_delay=0.1)
        
        # Mock operation: exception, success, success, success
        operation = AsyncMock(side_effect=[
            Exception("first failure"),
            "invalid_result",
            "another_invalid_result", 
            "success"
        ])
        
        # Mock validator: not called for exception, then fail, fail, success
        validator = MagicMock(side_effect=[
            (False, ["validation error 1"]),
            (False, ["validation error 2"]),
            (True, [])
        ])
        
        result = await handler.retry_with_validation(
            operation, validator, "test_operation"
        )
        
        assert result == "success"
        assert operation.call_count == 4
        assert validator.call_count == 3
        
    @pytest.mark.asyncio
    async def test_retry_with_validation_with_args_kwargs(self):
        """Test retry handler passes args and kwargs correctly"""
        handler = RetryHandler(max_retries=2, base_delay=0.1)
        
        # Mock operation that uses args and kwargs
        operation = AsyncMock(return_value="success")
        
        # Mock validator that passes
        validator = MagicMock(return_value=(True, []))
        
        result = await handler.retry_with_validation(
            operation, validator, "test_operation", 
            "arg1", "arg2", kwarg1="value1", kwarg2="value2"
        )
        
        assert result == "success"
        operation.assert_called_once_with("arg1", "arg2", kwarg1="value1", kwarg2="value2")
        validator.assert_called_once_with("success")


if __name__ == "__main__":
    pytest.main([__file__])
