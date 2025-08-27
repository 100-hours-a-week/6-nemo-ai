"""
Unit tests for Text Generation Model functionality.
Tests for app/models/text_generation_model.py
"""

import pytest
import asyncio
import json
import httpx
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Import from app instead of src
try:
    from app.models.text_generation_model import (
        call_vllm_api,
        stream_vllm_response,
        get_vllm_health_metrics,
        start_health_monitoring,
        _get_fallback_response,
        vllm_manager,
        queued_executor
    )
except ImportError:
    pytest.skip("Text generation model module not available", allow_module_level=True)


@pytest.mark.unit
class TestTextGenerationModel:
    """Unit tests for text generation model functionality."""

    def test_module_imports(self):
        """Test that all necessary components can be imported."""
        assert call_vllm_api is not None
        assert stream_vllm_response is not None
        assert get_vllm_health_metrics is not None
        assert start_health_monitoring is not None
        assert _get_fallback_response is not None
        assert vllm_manager is not None
        assert queued_executor is not None

    @pytest.mark.asyncio
    async def test_start_health_monitoring(self):
        """Test health monitoring startup."""
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = Mock()
            mock_task.done.return_value = True
            mock_create_task.return_value = mock_task
            
            with patch.object(vllm_manager, 'periodic_health_check', new_callable=AsyncMock) as mock_health_check:
                await start_health_monitoring()
                
                mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_vllm_health_metrics(self):
        """Test health metrics retrieval."""
        mock_base_metrics = {
            "circuit_breaker": {"state": "closed"},
            "health": {"success_rate": 0.95}
        }
        
        mock_queue_status = {
            "pending": 2,
            "active": 1,
            "completed": 100
        }
        
        with patch.object(vllm_manager, 'get_health_metrics', return_value=mock_base_metrics), \
             patch.object(queued_executor, 'get_queue_status', return_value=mock_queue_status):
            
            result = await get_vllm_health_metrics()
            
            assert "circuit_breaker" in result
            assert "health" in result
            assert "queue_status" in result
            assert result["queue_status"]["pending"] == 2

    @pytest.mark.asyncio
    async def test_call_vllm_api_success_string_prompt(self):
        """Test successful vLLM API call with string prompt."""
        with patch.object(queued_executor, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch('app.models.text_generation_model.start_health_monitoring', new_callable=AsyncMock) as mock_health:
            
            mock_submit.return_value = "Generated response"
            
            result = await call_vllm_api("Test prompt")
            
            assert result == "Generated response"
            mock_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_vllm_api_success_list_prompt(self):
        """Test successful vLLM API call with list prompt."""
        with patch.object(queued_executor, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch('app.models.text_generation_model.start_health_monitoring', new_callable=AsyncMock):
            
            mock_submit.return_value = ["Response 1", "Response 2"]
            
            result = await call_vllm_api(["Prompt 1", "Prompt 2"])
            
            assert result == ["Response 1", "Response 2"]

    @pytest.mark.asyncio
    async def test_call_vllm_api_empty_response_retry(self):
        """Test vLLM API call with empty response retry logic."""
        with patch.object(queued_executor, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch('app.models.text_generation_model.start_health_monitoring', new_callable=AsyncMock), \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep, \
             patch('app.models.text_generation_model._get_fallback_response', new_callable=AsyncMock) as mock_fallback:
            
            # First call returns empty, subsequent calls also empty
            mock_submit.side_effect = ["", "", ""]
            mock_fallback.return_value = "Fallback response"
            
            result = await call_vllm_api("Test prompt")
            
            assert result == "Fallback response"
            assert mock_submit.call_count == 3  # Original + 2 retries
            mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_vllm_api_exception_handling(self):
        """Test vLLM API call exception handling."""
        with patch.object(queued_executor, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch('app.models.text_generation_model.start_health_monitoring', new_callable=AsyncMock), \
             patch('app.models.text_generation_model._get_fallback_response', new_callable=AsyncMock) as mock_fallback:
            
            mock_submit.side_effect = Exception("API Error")
            mock_fallback.return_value = "Fallback response"
            
            result = await call_vllm_api("Test prompt")
            
            assert result == "Fallback response"
            mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_vllm_api_custom_parameters(self):
        """Test vLLM API call with custom parameters."""
        with patch.object(queued_executor, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch('app.models.text_generation_model.start_health_monitoring', new_callable=AsyncMock):
            
            mock_submit.return_value = "Custom response"
            
            result = await call_vllm_api("Test prompt", max_tokens=256, temperature=0.5)
            
            assert result == "Custom response"
            mock_submit.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_vllm_response_circuit_breaker_open(self):
        """Test streaming when circuit breaker is open."""
        messages = [{"role": "user", "text": "Hello"}]
        
        with patch.object(vllm_manager.circuit_breaker, 'is_request_allowed', new_callable=AsyncMock) as mock_allowed, \
             patch('asyncio.sleep', new_callable=AsyncMock):
            
            mock_allowed.return_value = False
            
            tokens = []
            async for token in stream_vllm_response(messages):
                tokens.append(token)
            
            # Should yield fallback message
            assert len(tokens) > 0
            fallback_text = "".join(tokens)
            assert "일시적인 오류" in fallback_text

    @pytest.mark.asyncio
    async def test_stream_vllm_response_exception_handling(self):
        """Test streaming exception handling."""
        messages = [{"role": "user", "text": "Hello"}]
        
        with patch('httpx.AsyncClient') as mock_client_class, \
             patch.object(vllm_manager.circuit_breaker, 'is_request_allowed', new_callable=AsyncMock) as mock_allowed, \
             patch.object(vllm_manager.circuit_breaker, 'record_failure', new_callable=AsyncMock) as mock_record_failure, \
             patch('app.models.text_generation_model.start_health_monitoring', new_callable=AsyncMock), \
             patch('asyncio.sleep', new_callable=AsyncMock):
            
            mock_allowed.return_value = True
            mock_client_class.side_effect = Exception("Network error")
            
            tokens = []
            async for token in stream_vllm_response(messages):
                tokens.append(token)
            
            # Should yield fallback content
            assert len(tokens) > 0
            fallback_text = "".join(tokens)
            assert "일시적인 오류" in fallback_text
            mock_record_failure.assert_called()

    @pytest.mark.asyncio
    async def test_get_fallback_response_question_generation(self):
        """Test fallback response for question generation prompts."""
        prompt = "다음을 참고하여 질문을 생성하세요. JSON으로만 출력하세요."
        
        result = await _get_fallback_response(prompt)
        
        assert isinstance(result, str)
        assert "question" in result
        assert "options" in result
        # Should be valid JSON
        parsed = json.loads(result)
        assert "question" in parsed
        assert "options" in parsed

    @pytest.mark.asyncio
    async def test_get_fallback_response_recommendation_explanation(self):
        """Test fallback response for recommendation explanation prompts."""
        prompt = "이 모임이 적합한 이유에 대한 설명을 작성하세요."
        
        result = await _get_fallback_response(prompt)
        
        assert isinstance(result, str)
        assert "추천" in result or "모임" in result
        assert len(result) > 10  # Should be a meaningful explanation

    @pytest.mark.asyncio
    async def test_get_fallback_response_list_prompt(self):
        """Test fallback response for list prompts."""
        prompts = ["질문 생성", "추천 설명"]
        
        result = await _get_fallback_response(prompts)
        
        assert isinstance(result, list)
        assert len(result) == len(prompts)
        for response in result:
            assert isinstance(response, str)
            assert len(response) > 0

    @pytest.mark.asyncio
    async def test_get_fallback_response_default_case(self):
        """Test fallback response for default case."""
        prompt = "일반적인 프롬프트입니다."
        
        result = await _get_fallback_response(prompt)
        
        assert isinstance(result, str)
        assert "모임" in result or "관심사" in result
        assert len(result) > 10

    def test_module_level_components(self):
        """Test that module-level components are properly initialized."""
        # Test that vllm_manager is initialized
        assert hasattr(vllm_manager, 'vllm_url')
        assert hasattr(vllm_manager, 'circuit_breaker')
        assert hasattr(vllm_manager, 'health_monitor')
        
        # Test that queued_executor is initialized
        assert hasattr(queued_executor, 'submit')

    @pytest.mark.asyncio
    async def test_call_vllm_api_with_logging(self):
        """Test vLLM API call logging integration."""
        with patch.object(queued_executor, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch('app.models.text_generation_model.start_health_monitoring', new_callable=AsyncMock), \
             patch('app.models.text_generation_model.ai_logger') as mock_logger:
            
            mock_submit.return_value = "Test response"
            
            result = await call_vllm_api("Test prompt")
            
            assert result == "Test response"
            # Verify logging calls were made
            mock_logger.info.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
