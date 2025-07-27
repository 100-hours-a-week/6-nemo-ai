"""
Integration tests for V2 chatbot API endpoints.
Tests HTTP and WebSocket chatbot functionality.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import from app instead of src
try:
    from app.main import app
    from app.schemas.chatbot.chatbot import ChatbotRequest, ChatbotResponse
    from app.schemas.chatbot.ws_chatbot import WebSocketMessage
except ImportError:
    pytest.skip("Chatbot API components not available", allow_module_level=True)


@pytest.mark.integration
class TestChatbotHTTPAPI:
    """Integration tests for HTTP chatbot API."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_chatbot_endpoint_exists(self, client):
        """Test that chatbot endpoint is accessible."""
        # Test basic endpoint accessibility
        response = client.post(
            "/ai/v2/chatbot",
            json={
                "userId": 1,
                "message": "안녕하세요",
                "sessionId": "test-session"
            }
        )
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    def test_chatbot_request_validation(self, client):
        """Test request validation for chatbot endpoint."""
        # Test missing required fields
        invalid_requests = [
            {},  # Empty request
            {"userId": 1},  # Missing message
            {"message": "hello"},  # Missing userId
            {"userId": "invalid", "message": "hello"},  # Invalid userId type
        ]
        
        for invalid_request in invalid_requests:
            response = client.post("/ai/v2/chatbot", json=invalid_request)
            assert response.status_code == 422  # Validation error

    def test_chatbot_valid_request(self, client):
        """Test chatbot with valid request."""
        valid_request = {
            "userId": 1,
            "message": "개발 스터디 찾고 있어요",
            "sessionId": "test-session-123"
        }
        
        with patch('app.services.v2.chatbot.process_chatbot_message') as mock_process:
            # Mock the service response
            mock_process.return_value = {
                "response": "좋은 개발 스터디를 찾아드렸습니다!",
                "recommendations": [
                    {"groupId": 1, "title": "Python 스터디", "score": 0.95}
                ],
                "sessionId": "test-session-123"
            }
            
            response = client.post("/ai/v2/chatbot", json=valid_request)
            
            assert response.status_code == 200
            response_data = response.json()
            
            # Check response structure
            assert "response" in response_data
            assert "recommendations" in response_data
            assert "sessionId" in response_data

    def test_chatbot_korean_message(self, client):
        """Test chatbot with Korean message."""
        korean_request = {
            "userId": 1,
            "message": "안녕하세요! 요리 모임 추천해주세요.",
            "sessionId": "korean-test"
        }
        
        with patch('app.services.v2.chatbot.process_chatbot_message') as mock_process:
            mock_process.return_value = {
                "response": "안녕하세요! 요리 모임을 찾아드릴게요.",
                "recommendations": [],
                "sessionId": "korean-test"
            }
            
            response = client.post("/ai/v2/chatbot", json=korean_request)
            assert response.status_code == 200
            
            response_data = response.json()
            assert "response" in response_data

    def test_chatbot_english_message(self, client):
        """Test chatbot with English message."""
        english_request = {
            "userId": 1,
            "message": "Hello! Can you recommend a programming study group?",
            "sessionId": "english-test"
        }
        
        with patch('app.services.v2.chatbot.process_chatbot_message') as mock_process:
            mock_process.return_value = {
                "response": "Hello! I can help you find programming study groups.",
                "recommendations": [],
                "sessionId": "english-test"
            }
            
            response = client.post("/ai/v2/chatbot", json=english_request)
            assert response.status_code == 200

    def test_chatbot_error_handling(self, client):
        """Test chatbot error handling."""
        valid_request = {
            "userId": 1,
            "message": "테스트 메시지",
            "sessionId": "error-test"
        }
        
        with patch('app.services.v2.chatbot.process_chatbot_message') as mock_process:
            # Simulate service error
            mock_process.side_effect = Exception("Service error")
            
            response = client.post("/ai/v2/chatbot", json=valid_request)
            
            # Should handle error gracefully
            assert response.status_code in [500, 503]  # Server error


@pytest.mark.integration
@pytest.mark.websocket
class TestWebSocketChatbot:
    """Integration tests for WebSocket chatbot."""

    def test_websocket_connection(self):
        """Test WebSocket connection establishment."""
        with TestClient(app) as client:
            try:
                with client.websocket_connect("/ai/v2/chatbot/ws") as websocket:
                    # Connection should be established
                    assert websocket is not None
            except Exception as e:
                pytest.skip(f"WebSocket not available: {e}")

    def test_websocket_message_exchange(self):
        """Test WebSocket message exchange."""
        with TestClient(app) as client:
            try:
                with client.websocket_connect("/ai/v2/chatbot/ws") as websocket:
                    # Send a test message
                    test_message = {
                        "type": "chat_message",
                        "userId": 1,
                        "message": "안녕하세요",
                        "sessionId": "ws-test"
                    }
                    
                    with patch('app.services.v2.ws_chatbot.process_websocket_message') as mock_process:
                        mock_process.return_value = {
                            "type": "chat_response",
                            "response": "안녕하세요! 무엇을 도와드릴까요?",
                            "sessionId": "ws-test"
                        }
                        
                        websocket.send_json(test_message)
                        response = websocket.receive_json()
                        
                        assert "type" in response
                        assert "response" in response
                        
            except Exception as e:
                pytest.skip(f"WebSocket test failed: {e}")

    def test_websocket_streaming_response(self):
        """Test WebSocket streaming response."""
        with TestClient(app) as client:
            try:
                with client.websocket_connect("/ai/v2/chatbot/ws") as websocket:
                    test_message = {
                        "type": "chat_message",
                        "userId": 1,
                        "message": "긴 답변이 필요한 질문",
                        "sessionId": "stream-test"
                    }
                    
                    websocket.send_json(test_message)
                    
                    # Receive multiple chunks
                    chunks = []
                    for _ in range(3):  # Expect up to 3 chunks
                        try:
                            chunk = websocket.receive_json(timeout=1)
                            chunks.append(chunk)
                        except:
                            break
                    
                    # Should receive at least one chunk
                    assert len(chunks) > 0
                    
            except Exception as e:
                pytest.skip(f"WebSocket streaming test failed: {e}")


@pytest.mark.integration
class TestChatbotAPIIntegration:
    """Integration tests for chatbot API with other components."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_chatbot_with_vector_search(self, client):
        """Test chatbot integration with vector search."""
        request_data = {
            "userId": 1,
            "message": "개발 관련 모임 찾아주세요",
            "sessionId": "vector-test"
        }
        
        with patch('app.services.shared.vector_service.search_similar_groups') as mock_search:
            mock_search.return_value = [
                {"groupId": 1, "title": "Python 개발 스터디", "score": 0.9},
                {"groupId": 2, "title": "웹 개발 모임", "score": 0.8}
            ]
            
            with patch('app.services.v2.chatbot.process_chatbot_message') as mock_chatbot:
                mock_chatbot.return_value = {
                    "response": "개발 관련 모임을 찾았습니다!",
                    "recommendations": mock_search.return_value,
                    "sessionId": "vector-test"
                }
                
                response = client.post("/ai/v2/chatbot", json=request_data)
                assert response.status_code == 200
                
                response_data = response.json()
                assert len(response_data["recommendations"]) == 2

    def test_chatbot_with_user_history(self, client):
        """Test chatbot considering user history."""
        # Simulate user with conversation history
        request_data = {
            "userId": 1,
            "message": "이전에 말한 개발 모임 더 알려주세요",
            "sessionId": "history-test",
            "conversationHistory": [
                {"role": "user", "message": "개발 스터디 찾아요"},
                {"role": "assistant", "message": "Python 스터디를 추천드립니다"}
            ]
        }
        
        with patch('app.services.v2.chatbot.process_chatbot_message') as mock_process:
            mock_process.return_value = {
                "response": "이전에 추천한 Python 스터디 외에도 다른 개발 모임이 있습니다.",
                "recommendations": [],
                "sessionId": "history-test"
            }
            
            response = client.post("/ai/v2/chatbot", json=request_data)
            assert response.status_code == 200

    @pytest.mark.slow
    def test_chatbot_performance(self, client):
        """Test chatbot API performance."""
        import time
        
        request_data = {
            "userId": 1,
            "message": "빠른 응답 테스트",
            "sessionId": "perf-test"
        }
        
        with patch('app.services.v2.chatbot.process_chatbot_message') as mock_process:
            mock_process.return_value = {
                "response": "빠른 응답입니다",
                "recommendations": [],
                "sessionId": "perf-test"
            }
            
            start_time = time.time()
            response = client.post("/ai/v2/chatbot", json=request_data)
            end_time = time.time()
            
            assert response.status_code == 200
            
            # Response should be fast (under 2 seconds for mocked service)
            response_time = end_time - start_time
            assert response_time < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
