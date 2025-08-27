"""
Unit tests for V2 chatbot.py
Tests chatbot functionality for question generation and answer analysis.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.v2.chatbot import (
    handle_combined_question,
    generate_combined_prompt,
    handle_answer_analysis,
    generate_explaination
)


class TestHandleCombinedQuestion:
    """Test handle_combined_question function"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies for handle_combined_question"""
        with patch('app.services.v2.chatbot.get_session_history') as mock_history, \
             patch('app.services.v2.chatbot.call_vllm_api') as mock_vllm, \
             patch('app.services.v2.chatbot.clean_prompt_context') as mock_clean, \
             patch('app.services.v2.chatbot.is_similar_to_any') as mock_similar, \
             patch('app.services.v2.chatbot.load_prompt_template') as mock_template:
            
            # Setup default mock behaviors
            mock_history_obj = MagicMock()
            mock_history.return_value = mock_history_obj
            mock_history_obj.get_messages.return_value = []
            
            mock_vllm.return_value = '{"question": "테스트 질문", "options": ["옵션1", "옵션2"]}'
            mock_clean.return_value = '{"question": "테스트 질문", "options": ["옵션1", "옵션2"]}'
            mock_similar.return_value = False
            mock_template.return_value = "test prompt"
            
            yield {
                'history': mock_history,
                'history_obj': mock_history_obj,
                'vllm': mock_vllm,
                'clean': mock_clean,
                'similar': mock_similar,
                'template': mock_template
            }
    
    @pytest.mark.asyncio
    async def test_debug_mode_returns_default_question(self, mock_dependencies):
        """Test debug mode returns predefined question"""
        result = await handle_combined_question(
            answer=None,
            user_id="test_user",
            session_id="test_session",
            debug_mode=True
        )
        
        assert result["question"] == "어떤 활동을 좋아하시나요?"
        assert result["options"] == ["운동", "스터디", "봉사활동", "게임"]
        
        # Should add question to history
        mock_dependencies['history_obj'].add_ai_message.assert_called_once_with("어떤 활동을 좋아하시나요?")
    
    @pytest.mark.asyncio
    async def test_successful_question_generation(self, mock_dependencies):
        """Test successful question generation from AI"""
        result = await handle_combined_question(
            answer="운동을 좋아합니다",
            user_id="test_user",
            session_id="test_session",
            debug_mode=False
        )
        
        assert result["question"] == "테스트 질문"
        assert result["options"] == ["옵션1", "옵션2"]
        
        # Verify AI API was called
        mock_dependencies['vllm'].assert_called_once()
        mock_dependencies['history_obj'].add_ai_message.assert_called_once_with("테스트 질문")
    
    @pytest.mark.asyncio
    async def test_similar_question_fallback(self, mock_dependencies):
        """Test fallback when generated question is similar to previous ones"""
        # Setup mock to detect similar question
        mock_dependencies['similar'].return_value = True
        mock_dependencies['history_obj'].get_messages.return_value = [
            {"role": "AI", "content": "이전 질문"}
        ]
        
        result = await handle_combined_question(
            answer="테스트 답변",
            user_id="test_user",
            session_id="test_session",
            debug_mode=False
        )
        
        assert result["question"] == "다른 사람과 함께 하고 싶은 활동은 무엇인가요?"
        assert result["options"] == ["문화 체험", "운동", "스터디", "봉사"]
    
    @pytest.mark.asyncio
    async def test_invalid_json_response_fallback(self, mock_dependencies):
        """Test fallback when AI returns invalid JSON"""
        mock_dependencies['vllm'].return_value = "Invalid response without JSON"
        mock_dependencies['clean'].return_value = "Invalid response without JSON"
        
        result = await handle_combined_question(
            answer="테스트 답변",
            user_id="test_user",
            session_id="test_session",
            debug_mode=False
        )
        
        assert result["question"] == "새로운 모임을 찾기 위해 어떤 활동을 선호하시나요?"
        assert result["options"] == ["문화 체험", "운동", "스터디", "봉사"]
    
    @pytest.mark.asyncio
    async def test_incomplete_json_response_fallback(self, mock_dependencies):
        """Test fallback when AI returns incomplete JSON"""
        mock_dependencies['vllm'].return_value = '{"question": ""}'  # Missing options
        mock_dependencies['clean'].return_value = '{"question": ""}'
        
        result = await handle_combined_question(
            answer="테스트 답변",
            user_id="test_user",
            session_id="test_session",
            debug_mode=False
        )
        
        assert result["question"] == "새로운 모임을 찾기 위해 어떤 활동을 선호하시나요?"
        assert result["options"] == ["문화 체험", "운동", "스터디", "봉사"]
    
    @pytest.mark.asyncio
    async def test_ai_api_exception_fallback(self, mock_dependencies):
        """Test fallback when AI API throws exception"""
        mock_dependencies['vllm'].side_effect = Exception("AI API 오류")
        
        result = await handle_combined_question(
            answer="테스트 답변",
            user_id="test_user",
            session_id="test_session",
            debug_mode=False
        )
        
        assert result["question"] == "새로운 모임을 찾기 위해 어떤 활동을 선호하시나요?"
        assert result["options"] == ["문화 체험", "운동", "스터디", "봉사"]


class TestGenerateCombinedPrompt:
    """Test generate_combined_prompt function"""
    
    @patch('app.services.v2.chatbot.load_prompt_template')
    def test_generate_prompt_with_previous_context(self, mock_template):
        """Test prompt generation with previous question and answer"""
        mock_template.return_value = "Generated prompt"
        
        result = generate_combined_prompt(
            previous_answer="운동을 좋아합니다",
            previous_question="어떤 활동을 좋아하시나요?"
        )
        
        # Verify template was called with context including both previous question and answer
        mock_template.assert_called_once()
        call_args = mock_template.call_args
        assert "이전 질문" in call_args[1]["context"]
        assert "사용자 답변" in call_args[1]["context"]
        
        assert result == "Generated prompt"
    
    @patch('app.services.v2.chatbot.load_prompt_template')
    def test_generate_prompt_with_answer_only(self, mock_template):
        """Test prompt generation with only previous answer"""
        mock_template.return_value = "Generated prompt"
        
        generate_combined_prompt(
            previous_answer="운동을 좋아합니다",
            previous_question=None
        )
        
        call_args = mock_template.call_args
        assert "사용자 답변" in call_args[1]["context"]
        assert "이전 질문" not in call_args[1]["context"]
    
    @patch('app.services.v2.chatbot.load_prompt_template')
    def test_generate_prompt_first_question(self, mock_template):
        """Test prompt generation for first question (no previous context)"""
        mock_template.return_value = "Generated prompt"
        
        generate_combined_prompt(
            previous_answer=None,
            previous_question=None
        )
        
        call_args = mock_template.call_args
        assert "첫 질문을 생성하세요" in call_args[1]["context"]


class TestHandleAnswerAnalysis:
    """Test handle_answer_analysis function"""
    
    @pytest.fixture
    def sample_messages(self):
        """Sample message data for testing"""
        return [
            {"role": "AI", "text": "어떤 활동을 좋아하시나요?"},
            {"role": "User", "text": "운동을 좋아합니다"},
            {"role": "AI", "text": "어떤 운동을 선호하시나요?"},
            {"role": "User", "text": "농구를 좋아합니다"}
        ]
    
    @pytest.mark.asyncio
    async def test_empty_messages_returns_no_recommendation(self):
        """Test handling of empty messages"""
        result = await handle_answer_analysis(
            messages=[],
            user_id="test_user",
            session_id="test_session"
        )
        
        assert result["groupId"] == -1
        assert "대화 내용이 부족" in result["reason"]
    
    @pytest.mark.asyncio
    @patch('app.services.v2.chatbot.get_user_joined_group_ids')
    @patch('app.services.v2.chatbot.search_similar_documents')
    @patch('app.services.v2.chatbot.generate_explaination')
    @patch('app.services.v2.chatbot.get_session_history')
    async def test_successful_recommendation(
        self, 
        mock_history,
        mock_explanation,
        mock_search,
        mock_joined_ids,
        sample_messages
    ):
        """Test successful recommendation generation"""
        # Setup mocks
        mock_joined_ids.return_value = set()
        mock_search.return_value = [
            {
                "metadata": {"groupId": "123"},
                "text": "농구 모임입니다"
            }
        ]
        mock_explanation.return_value = "농구를 좋아하셔서 이 모임을 추천합니다"
        
        mock_history_obj = MagicMock()
        mock_history.return_value = mock_history_obj
        
        # Execute
        result = await handle_answer_analysis(
            messages=sample_messages,
            user_id="test_user",
            session_id="test_session"
        )
        
        # Verify
        assert result["groupId"] == 123
        assert result["reason"] == "농구를 좋아하셔서 이 모임을 추천합니다"
        
        # Verify session was cleared
        mock_history_obj.clear.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.v2.chatbot.get_user_joined_group_ids')
    @patch('app.services.v2.chatbot.search_similar_documents')
    @patch('app.services.v2.chatbot.get_session_history')
    async def test_no_matching_groups(
        self,
        mock_history,
        mock_search,
        mock_joined_ids,
        sample_messages
    ):
        """Test when no matching groups are found"""
        # Setup mocks
        mock_joined_ids.return_value = set()
        mock_search.return_value = []  # No results
        
        mock_history_obj = MagicMock()
        mock_history.return_value = mock_history_obj
        
        # Execute
        result = await handle_answer_analysis(
            messages=sample_messages,
            user_id="test_user",
            session_id="test_session"
        )
        
        # Verify
        assert result["groupId"] == -1
        assert "추천 가능한 새로운 모임이" in result["reason"]
        
        # Verify session was cleared
        mock_history_obj.clear.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.v2.chatbot.get_user_joined_group_ids')
    @patch('app.services.v2.chatbot.search_similar_documents')
    @patch('app.services.v2.chatbot.generate_explaination')
    @patch('app.services.v2.chatbot.get_session_history')
    async def test_explanation_generation_failure(
        self,
        mock_history,
        mock_explanation,
        mock_search,
        mock_joined_ids,
        sample_messages
    ):
        """Test fallback when explanation generation fails"""
        # Setup mocks
        mock_joined_ids.return_value = set()
        mock_search.return_value = [
            {
                "metadata": {"groupId": "123"},
                "text": "농구 모임입니다"
            }
        ]
        mock_explanation.side_effect = Exception("설명 생성 실패")
        
        mock_history_obj = MagicMock()
        mock_history.return_value = mock_history_obj
        
        # Execute
        result = await handle_answer_analysis(
            messages=sample_messages,
            user_id="test_user",
            session_id="test_session"
        )
        
        # Verify fallback explanation is used
        assert result["groupId"] == 123
        assert result["reason"] == "이 모임은 당신의 대화 내용과 가장 잘 어울려 추천드립니다."


class TestGenerateExplanation:
    """Test generate_explaination function"""
    
    @pytest.fixture
    def sample_messages(self):
        """Sample message data for testing"""
        return [
            {"role": "AI", "text": "어떤 운동을 좋아하시나요?"},
            {"role": "User", "text": "농구를 좋아합니다"}
        ]
    
    @pytest.mark.asyncio
    @patch('app.services.v2.chatbot.call_vllm_api')
    @patch('app.services.v2.chatbot.clean_prompt_context')
    @patch('app.services.v2.chatbot.load_prompt_template')
    async def test_generate_explanation_success(
        self,
        mock_template,
        mock_clean,
        mock_vllm,
        sample_messages
    ):
        """Test successful explanation generation"""
        # Setup mocks
        mock_template.return_value = "test prompt"
        mock_vllm.return_value = "농구를 좋아하신다고 하셔서 이 농구 모임을 추천합니다"
        mock_clean.return_value = "농구를 좋아하신다고 하셔서 이 농구 모임을 추천합니다"
        
        # Execute
        result = await generate_explaination(
            messages=sample_messages,
            group_text="주말 농구 모임입니다",
            debug=False
        )
        
        # Verify
        assert "농구를 좋아하신다고 하셔서" in result
        
        # Verify API was called
        mock_vllm.assert_called_once()
        mock_template.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.v2.chatbot.call_vllm_api')
    @patch('app.services.v2.chatbot.clean_prompt_context')
    @patch('app.services.v2.chatbot.load_prompt_template')
    async def test_generate_explanation_cleans_prefixes(
        self,
        mock_template,
        mock_clean,
        mock_vllm,
        sample_messages
    ):
        """Test that explanation removes common AI prefixes"""
        # Setup mocks
        mock_template.return_value = "test prompt"
        mock_vllm.return_value = "AI: 농구를 좋아하신다고 하셔서 추천합니다"
        mock_clean.return_value = "AI: 농구를 좋아하신다고 하셔서 추천합니다"
        
        # Execute
        result = await generate_explaination(
            messages=sample_messages,
            group_text="주말 농구 모임입니다",
            debug=False
        )
        
        # Verify AI prefix is removed
        assert not result.startswith("AI:")
        assert "농구를 좋아하신다고 하셔서" in result


if __name__ == "__main__":
    pytest.main([__file__])
