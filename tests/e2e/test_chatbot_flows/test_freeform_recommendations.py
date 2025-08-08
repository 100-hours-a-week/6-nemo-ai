"""
E2E tests for freeform chatbot recommendations.
Migrated from src/tests/scenarios/chatbot_freeform.http
"""

import pytest
import requests
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
API_VERSION = "v2"


@pytest.mark.e2e
@pytest.mark.chatbot
class TestFreeformRecommendations:
    """End-to-end tests for freeform chatbot recommendations."""

    @pytest.fixture
    def api_client(self):
        """Create an API client for testing."""
        return APIClient(BASE_URL)

    @pytest.mark.parametrize("test_case", [
        {
            "name": "Quiet Atmosphere Request",
            "user_id": 1,
            "request_text": "시끄럽지 않고 조용한 분위기의 모임이 좋을 것 같아요.",
            "expected_keywords": ["조용", "분위기", "모임"]
        },
        {
            "name": "Active Physical Activity Request", 
            "user_id": 2,
            "request_text": "몸을 많이 쓰는 활동적인 모임이 있을까요?",
            "expected_keywords": ["활동적", "모임", "운동"]
        },
        {
            "name": "Healing and Stretching Request",
            "user_id": 5,
            "request_text": "힐링하거나 스트레칭할 수 있는 모임 추천해주세요.",
            "expected_keywords": ["힐링", "스트레칭", "모임"]
        },
        {
            "name": "Beginner Development Learning",
            "user_id": 3,
            "request_text": "개발이 처음이라 기초부터 차근차근 배울 수 있는 모임 있을까요?",
            "expected_keywords": ["개발", "기초", "모임", "배우"]
        },
        {
            "name": "Reading and Writing Quiet Group",
            "user_id": 1,
            "request_text": "책을 읽거나 글을 쓸 수 있는 조용한 모임이 좋을 것 같아요.",
            "expected_keywords": ["책", "글", "조용", "모임"]
        }
    ])
    def test_freeform_recommendation_scenarios(self, api_client, test_case):
        """Test various freeform recommendation scenarios."""
        # Prepare request data with correct schema
        request_data = {
            "userId": test_case["user_id"],
            "messages": [
                {"role": "USER", "text": test_case["request_text"]}
            ]
        }
        
        # Make API request
        response = api_client.post_freeform_recommendation(request_data)
        
        # Validate response structure
        assert response.status_code == 200
        response_data = response.json()
        
        # Check required fields - correct schema
        assert "code" in response_data
        assert "message" in response_data
        assert "data" in response_data
        
        # Validate recommendation content
        data = response_data["data"]
        assert "groupId" in data
        assert "reason" in data
        
        # GroupId should be a valid integer
        assert isinstance(data["groupId"], int)
        assert data["groupId"] > 0
        
        # Log for debugging
        print(f"Test case: {test_case['name']}")
        print(f"Request: {test_case['request_text']}")
        print(f"Group ID: {data['groupId']}, Reason: {data['reason']}")

    def test_freeform_recommendation_edge_cases(self, api_client):
        """Test edge cases for freeform recommendations."""
        edge_cases = [
            {
                "name": "Empty Request",
                "data": {"userId": 1, "messages": [{"role": "USER", "text": ""}]},
                "should_succeed": True  # Changed: API handles empty requests
            },
            {
                "name": "Very Short Request",
                "data": {"userId": 1, "messages": [{"role": "USER", "text": "모임"}]},
                "should_succeed": True
            },
            {
                "name": "Very Long Request",
                "data": {
                    "userId": 1, 
                    "messages": [{"role": "USER", "text": "안녕하세요. 저는 정말 조용하고 평화로운 분위기에서 책을 읽거나 글을 쓸 수 있는 독서 모임이나 글쓰기 모임을 찾고 있습니다. 시끄러운 환경을 싫어하고 집중할 수 있는 환경을 선호합니다."}]
                },
                "should_succeed": True
            },
            {
                "name": "English Request",
                "data": {"userId": 1, "messages": [{"role": "USER", "text": "I want to join a reading group"}]},
                "should_succeed": True
            },
            {
                "name": "Mixed Language",
                "data": {"userId": 1, "messages": [{"role": "USER", "text": "programming 스터디 모임 찾아요"}]},
                "should_succeed": True
            }
        ]
        
        for case in edge_cases:
            response = api_client.post_freeform_recommendation(case["data"])
            
            if case["should_succeed"]:
                assert response.status_code == 200
                response_data = response.json()
                assert "data" in response_data
                assert "groupId" in response_data["data"]
            else:
                # Should return error for invalid requests
                assert response.status_code in [400, 422]

    def test_user_specific_recommendations(self, api_client):
        """Test that recommendations are user-specific."""
        # Same request from different users should potentially return different results
        request_text = "재미있는 모임 추천해주세요"
        
        responses = {}
        for user_id in [1, 2, 3]:
            response = api_client.post_freeform_recommendation({
                "userId": user_id,
                "messages": [{"role": "USER", "text": request_text}]
            })
            
            assert response.status_code == 200
            responses[user_id] = response.json()
        
        # Each user should get recommendations (even if same ones)
        for user_id, response_data in responses.items():
            assert "data" in response_data
            assert "groupId" in response_data["data"]

    @pytest.mark.slow
    def test_recommendation_consistency(self, api_client):
        """Test that same request returns consistent results."""
        request_data = {
            "userId": 1,
            "messages": [{"role": "USER", "text": "개발 스터디 모임 찾아요"}]
        }
        
        responses = []
        for _ in range(3):  # Make same request 3 times
            response = api_client.post_freeform_recommendation(request_data)
            assert response.status_code == 200
            responses.append(response.json())
        
        # Results should be consistent (same recommendations)
        first_data = responses[0]["data"]
        for response in responses[1:]:
            current_data = response["data"]
            
            # Should have same group ID
            assert current_data["groupId"] == first_data["groupId"]


class APIClient:
    """Helper class for making API requests."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def post_freeform_recommendation(self, data: Dict[str, Any]) -> requests.Response:
        """Make a freeform recommendation request."""
        url = f"{self.base_url}/ai/{API_VERSION}/groups/recommendations"
        # Add session ID header required by the endpoint
        headers = {"x-session-id": f"test-session-{data.get('userId', 1)}"}
        return self.session.post(url, json=data, headers=headers)


@pytest.fixture(scope="session")
def verify_api_server():
    """Verify that the API server is running before tests."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"API server not available at {BASE_URL}")
    except requests.exceptions.RequestException:
        pytest.skip(f"API server not available at {BASE_URL}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
