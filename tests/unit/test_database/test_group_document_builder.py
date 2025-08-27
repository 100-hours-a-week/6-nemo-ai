"""
Unit tests for group_document_builder.py
Tests group document building functionality for vector database indexing.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.database.group_document_builder import (
    build_group_document,
    build_document_from_partial,
    remove_group_document,
    GROUP_COLLECTION
)


class TestBuildGroupDocument:
    """Test build_group_document function"""
    
    def setup_method(self):
        """Setup test data"""
        self.sample_group_response = {
            "groupId": "123",
            "name": "파이썬 스터디",
            "summary": "파이썬 프로그래밍을 배우는 스터디 모임",
            "description": "매주 파이썬 기초부터 심화까지 학습하며 프로젝트를 진행합니다.",
            "plan": "8주간 파이썬 기초 → 웹 개발 → 프로젝트",
            "tags": ["파이썬", "프로그래밍", "스터디"],
            "category": "기술",
            "location": "서울",
            "currentUserCount": 5,
            "maxUserCount": 10
        }
    
    def test_build_group_document_success(self):
        """Test successful group document building"""
        result = build_group_document(self.sample_group_response)
        
        # Verify document structure
        assert result["id"] == "group-123"
        assert "text" in result
        assert "metadata" in result
        
        # Verify text content includes key information
        text = result["text"]
        assert "파이썬 스터디" in text
        assert "기술" in text
        assert "서울" in text
        assert "파이썬 프로그래밍을 배우는" in text
        assert "8주간 파이썬 기초" in text
        assert "태그: 파이썬 프로그래밍 스터디" in text  # tags in text use spaces, not commas
        
        # Verify metadata
        metadata = result["metadata"]
        assert metadata["groupId"] == "123"
        assert metadata["id"] == "group-123"
        assert metadata["category"] == "기술"
        assert metadata["location"] == "서울"
        assert metadata["currentUserCount"] == 5
        assert metadata["maxUserCount"] == 10
        assert metadata["tags"] == "파이썬, 프로그래밍, 스터디"  # tags in metadata use commas
    
    def test_build_group_document_minimal_data(self):
        """Test building document with minimal required data"""
        minimal_response = {
            "groupId": "456",
            "name": "간단한 모임",
            "category": "취미",
            "location": "부산"
        }
        
        result = build_group_document(minimal_response)
        
        assert result["id"] == "group-456"
        assert "간단한 모임" in result["text"]
        assert "취미" in result["text"]
        assert "부산" in result["text"]
        
        # Should handle missing fields gracefully
        metadata = result["metadata"]
        assert "currentUserCount" not in metadata  # None values are filtered out
        assert "maxUserCount" not in metadata
    
    def test_build_group_document_invalid_group_id(self):
        """Test handling of invalid groupId"""
        invalid_responses = [
            {"groupId": None},
            {"groupId": ""},
            {"groupId": "None"},
            {}  # Missing groupId
        ]
        
        for response in invalid_responses:
            with pytest.raises(ValueError) as exc_info:
                build_group_document(response)
            assert "잘못된 groupId" in str(exc_info.value)
    
    def test_build_group_document_empty_tags(self):
        """Test handling of empty or None tags"""
        response_empty_tags = {
            "groupId": "789",
            "name": "태그 없는 모임",
            "tags": [],
            "category": "기타",
            "location": "대전"
        }
        
        result = build_group_document(response_empty_tags)
        
        # Should handle empty tags gracefully
        assert "태그:" not in result["text"]  # Empty tags not included
        assert result["metadata"]["tags"] == ""
        
        response_none_tags = {
            "groupId": "790",
            "name": "태그 없는 모임 2",
            "tags": None,
            "category": "기타",
            "location": "대전"
        }
        
        result = build_group_document(response_none_tags)
        assert result["metadata"]["tags"] == ""
    
    def test_build_group_document_empty_plan(self):
        """Test handling of empty plan"""
        response_no_plan = {
            "groupId": "800",
            "name": "계획 없는 모임",
            "plan": "",
            "category": "기타",
            "location": "인천"
        }
        
        result = build_group_document(response_no_plan)
        
        # Should not include empty plan in text
        assert "주요 계획:" not in result["text"]
    
    def test_build_group_document_numeric_group_id(self):
        """Test handling of numeric groupId"""
        response_numeric_id = {
            "groupId": 999,  # Numeric instead of string
            "name": "숫자 ID 모임",
            "category": "테스트",
            "location": "온라인"
        }
        
        result = build_group_document(response_numeric_id)
        
        assert result["id"] == "group-999"
        assert result["metadata"]["groupId"] == "999"  # Should be converted to string
    
    def test_build_group_document_string_user_counts(self):
        """Test handling of string user counts"""
        response_string_counts = {
            "groupId": "111",
            "name": "문자열 카운트 모임",
            "currentUserCount": "7",  # String instead of int
            "maxUserCount": "15",
            "category": "테스트",
            "location": "온라인"
        }
        
        result = build_group_document(response_string_counts)
        
        # Should convert to integers
        assert result["metadata"]["currentUserCount"] == 7
        assert result["metadata"]["maxUserCount"] == 15


class TestBuildDocumentFromPartial:
    """Test build_document_from_partial function"""
    
    def test_build_partial_document_all_fields(self):
        """Test building partial document with all possible fields"""
        partial_update = {
            "name": "새로운 모임 이름",
            "summary": "새로운 한줄 소개",
            "description": "새로운 상세 설명",
            "plan": "새로운 계획",
            "tags": ["새로운", "태그"]
        }
        
        result = build_document_from_partial(partial_update, "123")
        
        assert result["id"] == "group-123"
        assert "[모임 이름] 새로운 모임 이름" in result["text"]
        assert "[한줄 소개] 새로운 한줄 소개" in result["text"]
        assert "[설명] 새로운 상세 설명" in result["text"]
        assert "[계획] 새로운 계획" in result["text"]
        assert "[태그] 새로운 태그" in result["text"]
        assert result["metadata"] == partial_update
    
    def test_build_partial_document_single_field(self):
        """Test building partial document with single field"""
        partial_update = {"name": "업데이트된 이름"}
        
        result = build_document_from_partial(partial_update, "456")
        
        assert result["id"] == "group-456"
        assert result["text"] == "[모임 이름] 업데이트된 이름"
        assert result["metadata"] == partial_update
    
    def test_build_partial_document_empty_update(self):
        """Test building partial document with empty update"""
        partial_update = {}
        
        result = build_document_from_partial(partial_update, "789")
        
        assert result["id"] == "group-789"
        assert result["text"] == ""
        assert result["metadata"] == {}
    
    def test_build_partial_document_numeric_group_id(self):
        """Test building partial document with numeric group ID"""
        partial_update = {"summary": "숫자 ID 테스트"}
        
        result = build_document_from_partial(partial_update, 999)
        
        assert result["id"] == "group-999"


class TestRemoveGroupDocument:
    """Test remove_group_document function"""
    
    @patch('app.database.group_document_builder.get_chroma_client')
    @patch('app.database.group_document_builder.embed')
    def test_remove_group_document_success(self, mock_embed, mock_get_client):
        """Test successful group document removal"""
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Execute
        remove_group_document("123")
        
        # Verify
        mock_client.get_or_create_collection.assert_called_once_with(
            name=GROUP_COLLECTION,
            embedding_function=mock_embed
        )
        mock_collection.delete.assert_called_once_with(ids=["group-123"])
    
    @patch('app.database.group_document_builder.get_chroma_client')
    @patch('app.database.group_document_builder.embed')
    def test_remove_group_document_with_string_id(self, mock_embed, mock_get_client):
        """Test removing group document with string ID"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Execute
        remove_group_document("test-group-456")
        
        # Verify correct document ID is used
        mock_collection.delete.assert_called_once_with(ids=["group-test-group-456"])


if __name__ == "__main__":
    pytest.main([__file__])
