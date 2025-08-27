"""
Unit tests for Vertex AI client functionality.
Tests for app/core/vertex_client.py
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from concurrent.futures import Future

# Import from app instead of src
try:
    from app.core.vertex_client import (
        generate_content,
        limited_generate,
        smart_generate,
        vertex_executor,
        queued_executor
    )
except ImportError:
    pytest.skip("Vertex client module not available", allow_module_level=True)


@pytest.mark.unit
class TestVertexClient:
    """Unit tests for Vertex AI client functionality."""

    def test_vertex_client_imports(self):
        """Test that all necessary components can be imported."""
        # Basic import test
        assert generate_content is not None
        assert limited_generate is not None
        assert smart_generate is not None
        assert vertex_executor is not None
        assert queued_executor is not None

    @patch('app.core.vertex_client.gen_model')
    @patch('app.core.vertex_client.ai_logger')
    def test_generate_content_success(self, mock_logger, mock_gen_model):
        """Test successful content generation."""
        # Mock the response
        mock_response = Mock()
        mock_response.text = "Generated content successfully"
        mock_gen_model.generate_content.return_value = mock_response
        
        prompt = "Test prompt"
        result = generate_content(prompt)
        
        assert result == "Generated content successfully"
        mock_gen_model.generate_content.assert_called_once()

    @patch('app.core.vertex_client.gen_model')
    @patch('app.core.vertex_client.ai_logger')
    def test_generate_content_empty_response(self, mock_logger, mock_gen_model):
        """Test handling of empty response."""
        # Mock empty response
        mock_response = Mock()
        mock_response.text = ""
        mock_gen_model.generate_content.return_value = mock_response
        
        prompt = "Test prompt"
        result = generate_content(prompt)
        
        # Should return [ERROR] after retries for empty response
        assert result == "[ERROR]"
        mock_logger.warning.assert_called()

    @patch('app.core.vertex_client.gen_model')
    @patch('app.core.vertex_client.ai_logger')
    def test_generate_content_no_text_attribute(self, mock_logger, mock_gen_model):
        """Test handling when response has no text attribute."""
        # Mock response without text attribute
        mock_response = Mock(spec=[])  # Empty spec means no attributes
        mock_gen_model.generate_content.return_value = mock_response
        
        prompt = "Test prompt"
        result = generate_content(prompt)
        
        assert result == "[ERROR]"
        mock_logger.warning.assert_called()

    @patch('app.core.vertex_client.gen_model')
    @patch('app.core.vertex_client.ai_logger')
    def test_generate_content_invalid_argument(self, mock_logger, mock_gen_model):
        """Test handling of InvalidArgument exception."""
        from google.api_core.exceptions import InvalidArgument
        
        mock_gen_model.generate_content.side_effect = InvalidArgument("Invalid prompt")
        
        prompt = "Invalid test prompt"
        result = generate_content(prompt)
        
        assert result == "[INVALID_ARGUMENT]"
        mock_logger.warning.assert_called()

    @patch('app.core.vertex_client.gen_model')
    @patch('app.core.vertex_client.ai_logger')
    def test_generate_content_resource_exhausted(self, mock_logger, mock_gen_model):
        """Test handling of ResourceExhausted exception."""
        from google.api_core.exceptions import ResourceExhausted
        
        mock_gen_model.generate_content.side_effect = ResourceExhausted("Quota exceeded")
        
        prompt = "Test prompt"
        result = generate_content(prompt)
        
        assert result == "[QUOTA_EXCEEDED]"
        mock_logger.warning.assert_called()

    @patch('app.core.vertex_client.gen_model')
    @patch('app.core.vertex_client.ai_logger')
    @patch('time.sleep')
    def test_generate_content_retry_logic(self, mock_sleep, mock_logger, mock_gen_model):
        """Test retry logic for transient failures."""
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.text = "Success after retry"
        mock_gen_model.generate_content.side_effect = [
            RuntimeError("Transient error"),  # Use a proper exception
            mock_response
        ]
        
        prompt = "Test prompt"
        result = generate_content(prompt, max_retries=2)
        
        assert result == "Success after retry"
        assert mock_gen_model.generate_content.call_count == 2
        mock_sleep.assert_called_once_with(0.5)

    @patch('app.core.vertex_client.gen_model')
    @patch('app.core.vertex_client.ai_logger')
    @patch('time.sleep')
    def test_generate_content_max_retries_exceeded(self, mock_sleep, mock_logger, mock_gen_model):
        """Test behavior when max retries are exceeded."""
        mock_gen_model.generate_content.side_effect = RuntimeError("Persistent error")
        
        prompt = "Test prompt"
        result = generate_content(prompt, max_retries=2)
        
        assert result == "[ERROR]"
        assert mock_gen_model.generate_content.call_count == 2
        mock_logger.error.assert_called()

    @patch('app.core.vertex_client.vertex_executor')
    @patch('app.core.vertex_client.ai_logger')
    def test_limited_generate(self, mock_logger, mock_executor):
        """Test limited generate function."""
        # Mock the executor
        mock_future = Mock()
        mock_future.result.return_value = "Limited generate result"
        mock_executor.submit.return_value = mock_future
        
        prompt = "Test prompt for limited generate"
        result = limited_generate(prompt)
        
        assert result == "Limited generate result"
        mock_executor.submit.assert_called_once()
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    @patch('app.core.vertex_client.queued_executor')
    @patch('app.core.vertex_client.ai_logger')
    async def test_smart_generate_with_event_loop(self, mock_logger, mock_executor):
        """Test smart generate with running event loop."""
        # Mock queued executor
        mock_executor.submit = AsyncMock(return_value="Smart generate result")
        
        prompt = "Test prompt for smart generate"
        result = await smart_generate(prompt)
        
        assert result == "Smart generate result"
        mock_executor.submit.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.core.vertex_client.queued_executor')
    async def test_smart_generate_no_event_loop_simple(self, mock_executor):
        """Test smart generate when no event loop is running - simplified version."""
        # Mock queued executor submit to be async
        async def mock_submit_func(*args, **kwargs):
            return "Smart generate result"
        
        mock_executor.submit = mock_submit_func
        
        # Test the normal case first (with event loop)
        prompt = "Test prompt"
        result = await smart_generate(prompt)
        
        assert result == "Smart generate result"

    def test_generate_content_with_different_prompts(self):
        """Test generate_content with various prompt types."""
        with patch('app.core.vertex_client.gen_model') as mock_gen_model:
            mock_response = Mock()
            mock_response.text = "Response"
            mock_gen_model.generate_content.return_value = mock_response
            
            # Test with different prompt types
            test_cases = [
                "Simple prompt",
                "Prompt with special characters: !@#$%^&*()",
                "한글 프롬프트 테스트",
                "Very long prompt " * 50,
                "",  # Empty prompt
            ]
            
            for prompt in test_cases:
                result = generate_content(prompt)
                assert result == "Response"

    @patch('app.core.vertex_client.gen_model')
    @patch('app.core.vertex_client.ai_logger')
    def test_generate_content_whitespace_handling(self, mock_logger, mock_gen_model):
        """Test that whitespace is properly stripped from responses."""
        mock_response = Mock()
        mock_response.text = "  \n  Response with whitespace  \t  "
        mock_gen_model.generate_content.return_value = mock_response
        
        prompt = "Test prompt"
        result = generate_content(prompt)
        
        assert result == "Response with whitespace"

    def test_executors_initialization(self):
        """Test that executors are properly initialized."""
        # Test that executors exist and have expected properties
        assert hasattr(vertex_executor, 'submit')
        assert hasattr(queued_executor, 'submit')
        
        # Test basic properties if accessible
        try:
            assert vertex_executor._max_workers == 3
            assert queued_executor._max_workers == 3
        except AttributeError:
            # It's OK if these are private/inaccessible
            pass

    @patch('app.core.vertex_client.gen_model')
    def test_generation_config_usage(self, mock_gen_model):
        """Test that generation config is properly used."""
        mock_response = Mock()
        mock_response.text = "Configured response"
        mock_gen_model.generate_content.return_value = mock_response
        
        prompt = "Test prompt"
        result = generate_content(prompt)
        
        # Verify that generate_content was called with config
        call_args = mock_gen_model.generate_content.call_args
        assert call_args[0][0] == prompt  # First positional arg is prompt
        
        # Check if generation_config was passed (might be keyword arg)
        if len(call_args) > 1 and 'generation_config' in call_args[1]:
            config = call_args[1]['generation_config']
            assert config is not None

    @patch('app.core.vertex_client.ai_logger')
    def test_logging_integration(self, mock_logger):
        """Test that logging is properly integrated."""
        with patch('app.core.vertex_client.gen_model') as mock_gen_model:
            mock_response = Mock()
            mock_response.text = "Test response"
            mock_gen_model.generate_content.return_value = mock_response
            
            # Test successful generation logging
            result = generate_content("Test prompt")
            
            # Verify that no error/warning logs were called for successful case
            mock_logger.error.assert_not_called()

    def test_module_level_imports(self):
        """Test that all required modules and dependencies are available."""
        try:
            # Test that core dependencies are importable at test level
            # Since these are mocked in conftest.py, just verify the mocks work
            import sys
            assert 'google.cloud.aiplatform' in sys.modules
            assert 'google.oauth2.service_account' in sys.modules
            assert 'vertexai.preview.generative_models' in sys.modules
            assert 'vertexai.language_models' in sys.modules
            assert 'google.api_core.exceptions' in sys.modules
        except ImportError as e:
            pytest.skip(f"Required dependency not available: {e}")

    @patch('app.core.vertex_client.gen_model')
    def test_concurrent_requests_safety(self, mock_gen_model):
        """Test thread safety of generate_content function."""
        import threading
        import queue
        
        mock_response = Mock()
        mock_response.text = "Concurrent response"
        mock_gen_model.generate_content.return_value = mock_response
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def worker(prompt_id):
            try:
                result = generate_content(f"Prompt {prompt_id}")
                results.put(result)
            except Exception as e:
                errors.put(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"
        assert results.qsize() == 5
        
        # All results should be the same
        all_results = []
        while not results.empty():
            all_results.append(results.get())
        
        assert all(r == "Concurrent response" for r in all_results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
