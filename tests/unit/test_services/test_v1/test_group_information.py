"""
Unit tests for V1 group_information.py
Tests the build_meeting_data function for generating meeting data with AI services.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.v1.group_information import build_meeting_data
from app.schemas.groups.group_information import MeetingInput, MeetingData
from app.schemas.groups.group_writer import GroupGenerationRequest


class TestBuildMeetingData:
    """Test build_meeting_data function"""
    
    @pytest.fixture
    def sample_meeting_input(self):
        """Create sample meeting input for testing"""
        return MeetingInput(
            name="파이썬 스터디",
            goal="파이썬 프로그래밍 실력 향상",
            category="프로그래밍",
            period="8주",
            isPlanCreated=True
        )
    
    @pytest.fixture
    def sample_meeting_input_no_plan(self):
        """Create sample meeting input without plan for testing"""
        return MeetingInput(
            name="요리 모임",
            goal="다양한 요리 배우기",
            category="취미",
            period="4주",
            isPlanCreated=False
        )
    
    @pytest.mark.asyncio
    @patch('app.services.v1.group_information.generate_description')
    @patch('app.services.v1.group_information.extract_tags')
    @patch('app.services.v1.group_information.generate_plan')
    async def test_build_meeting_data_success_with_plan(
        self, 
        mock_generate_plan,
        mock_extract_tags,
        mock_generate_description,
        sample_meeting_input
    ):
        """Test successful meeting data generation with plan"""
        # Setup mocks
        mock_generate_description.return_value = ("짧은 요약", "상세한 설명입니다.")
        mock_extract_tags.return_value = ["파이썬", "프로그래밍", "스터디"]
        mock_generate_plan.return_value = "상세한 계획입니다."
        
        # Execute
        result = await build_meeting_data(sample_meeting_input)
        
        # Verify
        assert isinstance(result, MeetingData)
        assert result.name == "파이썬 스터디"
        assert result.summary == "짧은 요약"
        assert result.description == "상세한 설명입니다."
        assert result.tags == ["파이썬", "프로그래밍", "스터디"]
        assert result.plan == "상세한 계획입니다."
        
        # Verify calls
        mock_generate_description.assert_called_once()
        called_args = mock_generate_description.call_args[0][0]
        assert isinstance(called_args, GroupGenerationRequest)
        assert called_args.name == "파이썬 스터디"
        assert called_args.goal == "파이썬 프로그래밍 실력 향상"
        assert called_args.isPlanCreated == True
        
        mock_extract_tags.assert_called_once_with("상세한 설명입니다.")
        mock_generate_plan.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.v1.group_information.generate_description')
    @patch('app.services.v1.group_information.extract_tags')
    @patch('app.services.v1.group_information.generate_plan')
    async def test_build_meeting_data_success_without_plan(
        self, 
        mock_generate_plan,
        mock_extract_tags,
        mock_generate_description,
        sample_meeting_input_no_plan
    ):
        """Test successful meeting data generation without plan"""
        # Setup mocks
        mock_generate_description.return_value = ("요리 요약", "요리 모임 설명")
        mock_extract_tags.return_value = ["요리", "취미"]
        
        # Execute
        result = await build_meeting_data(sample_meeting_input_no_plan)
        
        # Verify
        assert isinstance(result, MeetingData)
        assert result.name == "요리 모임"
        assert result.summary == "요리 요약"
        assert result.description == "요리 모임 설명"
        assert result.tags == ["요리", "취미"]
        assert result.plan is None
        
        # Verify plan generation was not called
        mock_generate_plan.assert_not_called()
        
        # Verify other calls
        mock_generate_description.assert_called_once()
        mock_extract_tags.assert_called_once_with("요리 모임 설명")
    
    @pytest.mark.asyncio
    @patch('app.services.v1.group_information.generate_description')
    @patch('app.services.v1.group_information.extract_tags')
    @patch('app.services.v1.group_information.generate_plan')
    async def test_build_meeting_data_all_retries_fail(
        self, 
        mock_generate_plan,
        mock_extract_tags,
        mock_generate_description,
        sample_meeting_input
    ):
        """Test behavior when all retries fail"""
        # Setup mocks to always fail
        mock_generate_description.side_effect = Exception("Service unavailable")
        
        # Execute
        result = await build_meeting_data(sample_meeting_input)
        
        # Verify fallback behavior
        assert isinstance(result, MeetingData)
        assert result.name == "파이썬 스터디"
        assert result.summary == ""
        assert result.description == ""
        assert result.tags == []
        assert result.plan is None
        
        # Verify all retries were attempted
        assert mock_generate_description.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__])
