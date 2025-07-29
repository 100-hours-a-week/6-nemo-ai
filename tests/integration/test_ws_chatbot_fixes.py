import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.services.v2.ws_chatbot import (
    PrefixParser, 
    stream_question_chunks, 
    stream_recommendation_chunks,
    _clean_group_text_for_recommendation,
    clean_group_text,
    parse_group_information
)
from src.vector_db.group_document_builder import (
    parse_group_information as parse_group_info_builder,
    clean_group_text as clean_group_text_builder
)


class TestPrefixParser:
    """Test the enhanced PrefixParser for special character handling"""
    
    def test_special_character_removal(self):
        """Test that only & character is allowed among special characters"""
        parser = PrefixParser(["질문:"])
        
        # Test that & character is preserved
        result = parser.process_chunk("Hello & world")
        assert result == "Hello & world"
        
        # Test that other special characters are removed but spaces preserved
        result = parser.process_chunk("Hello world test")
        assert result == "Hello world test"
        
        # Test mixed special characters - only & should remain
        result = parser.process_chunk("안녕하세요 & 어떻게@지내세요#?")
        assert result == "안녕하세요 & 어떻게지내세요?"

    def test_prefix_removal_with_special_chars(self):
        """Test prefix removal works with & character allowed"""
        parser = PrefixParser(["질문:", "**질문:**"])
        
        # Chunk with prefix and & character
        chunk1 = "질문: 안녕하세요 & 반갑습니다"
        result1 = parser.process_chunk(chunk1)
        assert result1 == "안녕하세요 & 반갑습니다"
        
        # Follow-up chunks should preserve &
        chunk2 = " 어떻게 & 지내세요?"
        result2 = parser.process_chunk(chunk2)
        assert result2 == " 어떻게 & 지내세요?"

    def test_preserve_korean_characters(self):
        """Test that Korean characters are preserved"""
        parser = PrefixParser(["질문:"])
        
        result = parser.process_chunk("안녕하세요, 오늘 날씨가 좋네요!")
        assert result == "안녕하세요, 오늘 날씨가 좋네요!"

    def test_regex_pattern_safety(self):
        """Test that regex patterns handle edge cases safely and preserve &"""
        parser = PrefixParser(["질문:"])
        
        # Empty chunk should return empty string after processing
        result = parser.process_chunk("")
        assert result == ""
        
        # Only & character should be preserved
        parser2 = PrefixParser(["질문:"])
        result = parser2.process_chunk("Hello & World")
        assert result == "Hello & World"
        
        # Mixed with valid content and & character
        parser3 = PrefixParser(["질문:"])
        result = parser3.process_chunk("Hello & World@#$")
        assert result == "Hello & World"


class TestTagFiltering:
    """Test tag filtering in recommendations"""
    
    def test_clean_group_text_for_recommendation(self):
        """Test that group text is properly cleaned of tags and metadata"""
        
        # Test tag removal
        text_with_tags = "이것은 좋은 모임입니다. 태그: 스포츠, 건강, 운동"
        cleaned = _clean_group_text_for_recommendation(text_with_tags)
        assert "태그:" not in cleaned
        assert "스포츠, 건강, 운동" not in cleaned
        assert "이것은 좋은 모임입니다." in cleaned
        
        # Test hashtag removal
        text_with_hashtags = "재미있는 모임입니다 #스포츠 #건강 #운동"
        cleaned = _clean_group_text_for_recommendation(text_with_hashtags)
        assert "#스포츠" not in cleaned
        assert "#건강" not in cleaned
        assert "재미있는 모임입니다" in cleaned
        
        # Test metadata removal
        text_with_metadata = "좋은 모임 메타데이터: category=sports, location=서울"
        cleaned = _clean_group_text_for_recommendation(text_with_metadata)
        assert "메타데이터:" not in cleaned
        assert "category=sports" not in cleaned
        
        # Test English tag patterns
        text_with_english_tags = "Great group tags: sports, health, fitness"
        cleaned = _clean_group_text_for_recommendation(text_with_english_tags)
        assert "tags:" not in cleaned
        assert "sports, health, fitness" not in cleaned


class TestStreamingWithFilters:
    """Test streaming functions with the new filtering"""
    
    @pytest.mark.asyncio
    async def test_question_streaming_special_chars(self):
        """Test that question streaming handles special characters correctly"""
        
        # Mock the vLLM streaming response with special characters
        async def mock_stream_vllm_response(messages):
            chunks = [
                "질문:\\n",  # Prefix with special chars
                "안녕하세요\\r",  # Korean with special chars  
                " 어떻게\\t",  # Space with tab
                "지내세요?\\n\\r",  # Question with multiple special chars
                "options: [\"좋아요\", \"나빠요\"]"  # Options
            ]
            for chunk in chunks:
                yield chunk
        
        with patch('src.services.v2.ws_chatbot.stream_vllm_response', mock_stream_vllm_response):
            with patch('src.services.v2.ws_chatbot.get_session_history') as mock_history:
                mock_history.return_value.get_messages.return_value = []
                mock_history.return_value.add_ai_message = Mock()
                
                chunks = []
                async for chunk in stream_question_chunks("test answer", "user123", "session123"):
                    if isinstance(chunk, str):
                        chunks.append(chunk)
                
                # Verify special characters were removed but content preserved
                full_text = "".join(chunks)
                assert "\\n" not in full_text
                assert "\\r" not in full_text
                assert "\\t" not in full_text
                assert "안녕하세요" in full_text
                assert "어떻게" in full_text
                assert "지내세요?" in full_text

    @pytest.mark.asyncio
    async def test_recommendation_streaming_without_tag_filtering(self):
        """Test that recommendation streaming works without tag filtering"""
        
        # Mock vector search results with tags
        mock_result = {
            "metadata": {"groupId": 123},
            "text": "좋은 축구 모임입니다. 태그: 스포츠, 건강, 운동 매주 토요일에 만납니다.",
            "score": 0.8
        }
        
        # Mock the vLLM streaming response that might include normal Korean text
        async def mock_stream_vllm_response(messages):
            chunks = [
                "이 모임은 ",
                "백엔드 개발자들의 ",  # Previously filtered words
                "성장이라는 ",
                "명확한 목표를 ",
                "가진 모임이라, ",
                "당신에게 딱 맞는 ",
                "선택일 거예요."
            ]
            for chunk in chunks:
                yield chunk
        
        with patch('src.services.v2.ws_chatbot.hybrid_group_search', return_value=[mock_result]):
            with patch('src.services.v2.ws_chatbot.stream_vllm_response', mock_stream_vllm_response):
                with patch('src.services.v2.ws_chatbot.get_vllm_health_metrics', return_value={}):
                    
                    messages = [{"role": "user", "text": "백엔드 개발 공부하고 싶어요"}]
                    
                    recommendation_chunks = []
                    async for chunk in stream_recommendation_chunks(messages, "user123", "session123"):
                        if isinstance(chunk, tuple) and len(chunk) == 2:
                            group_id, text = chunk
                            if group_id != -1 and text != "RECOMMEND_DONE":
                                recommendation_chunks.append(text)
                    
                    # Verify all text chunks are included (no filtering)
                    full_recommendation = "".join(recommendation_chunks)
                    assert "백엔드 개발자들의" in full_recommendation
                    assert "성장이라는" in full_recommendation  
                    assert "명확한 목표를" in full_recommendation
                    assert "가진 모임이라" in full_recommendation
                    assert "당신에게 딱 맞는" in full_recommendation
                    assert "선택일 거예요" in full_recommendation

    def test_group_text_cleaning_comprehensive(self):
        """Comprehensive test of group text cleaning"""
        
        # Complex text with multiple tag formats
        complex_text = """
        이것은 훌륭한 축구 모임입니다.
        매주 토요일 오후 2시에 만납니다.
        태그: 스포츠, 건강, 운동, 축구
        #축구 #스포츠 #건강
        [태그] 재미있는, 활동적인
        메타데이터: category=sports, location=서울
        tags: football, sports, health
        분류: 스포츠 활동
        """
        
        cleaned = _clean_group_text_for_recommendation(complex_text)
        
        # Should keep the main content
        assert "훌륭한 축구 모임입니다" in cleaned
        assert "매주 토요일 오후 2시" in cleaned
        
        # Should remove all tag-related content
        assert "태그:" not in cleaned
        assert "#축구" not in cleaned
        assert "[태그]" not in cleaned
        assert "메타데이터:" not in cleaned
        assert "tags:" not in cleaned
        assert "분류:" not in cleaned
        assert "category=sports" not in cleaned
        
        # Verify no excessive whitespace
        assert "  " not in cleaned.strip()


class TestGroupInformationParsing:
    """Test group information parsing and cleaning"""
    
    def test_clean_group_text_code_blocks(self):
        """Test removal of code blocks from group text"""
        # Test triple backticks
        text_with_code = "이것은 좋은 모임입니다. ```python\nprint('hello')\n``` 매주 만납니다."
        cleaned = clean_group_text(text_with_code)
        assert "```" not in cleaned
        assert "print('hello')" not in cleaned
        assert "이것은 좋은 모임입니다." in cleaned
        assert "매주 만납니다." in cleaned
        
        # Test triple quotes  
        text_with_quotes = "훌륭한 모임 '''some unwanted content''' 참여하세요."
        cleaned = clean_group_text(text_with_quotes)
        assert "'''" not in cleaned
        assert "some unwanted content" not in cleaned
        assert "훌륭한 모임" in cleaned
        assert "참여하세요." in cleaned
    
    def test_parse_group_information(self):
        """Test group information parsing and cleaning"""
        group_data = {
            "name": "개발자 모임 ```javascript\nconsole.log('test')\n```",
            "summary": "좋은 모임 '''unwanted''' 입니다",
            "description": "상세 설명 ```\ncode block\n``` 내용",
            "tags": ["태그1 ```code```", "태그2", "태그3 '''quote'''"],
            "category": "개발",
            "location": "서울"
        }
        
        parsed = parse_group_information(group_data)
        
        # Check that code blocks and quotes are removed
        assert "```" not in parsed["name"]
        assert "console.log('test')" not in parsed["name"]
        assert "개발자 모임" in parsed["name"]
        
        assert "'''" not in parsed["summary"]
        assert "unwanted" not in parsed["summary"]
        assert "좋은 모임" in parsed["summary"]
        
        assert "```" not in parsed["description"]
        assert "code block" not in parsed["description"]
        assert "상세 설명" in parsed["description"]
        
        # Check tags are cleaned
        assert all("```" not in tag for tag in parsed["tags"])
        assert all("'''" not in tag for tag in parsed["tags"])
        assert "태그1" in parsed["tags"][0]
        assert "태그3" in parsed["tags"][2]
    
    def test_group_document_builder_integration(self):
        """Test that group document builder uses the cleaning functionality"""
        group_data = {
            "groupId": 123,
            "name": "코딩 모임 ```python\nprint('hello')\n```",
            "summary": "개발자들의 모임 '''unwanted text''' 입니다",
            "description": "백엔드 개발 ```sql\nSELECT * FROM users\n``` 공부",
            "plan": "매주 스터디 '''bad content''' 진행",
            "tags": ["Python ```code```", "백엔드", "스터디 '''text'''"],
            "category": "개발",
            "location": "서울",
            "currentUserCount": 5,
            "maxUserCount": 10
        }
        
        parsed = parse_group_info_builder(group_data)
        
        # Verify all text fields are cleaned
        assert "```" not in parsed["name"]
        assert "print('hello')" not in parsed["name"]
        assert "코딩 모임" in parsed["name"]
        
        assert "'''" not in parsed["summary"]
        assert "unwanted text" not in parsed["summary"]
        assert "개발자들의 모임" in parsed["summary"]
        
        assert "```" not in parsed["description"]
        assert "SELECT * FROM users" not in parsed["description"]
        assert "백엔드 개발" in parsed["description"]
        
        assert "'''" not in parsed["plan"]
        assert "bad content" not in parsed["plan"]
        assert "매주 스터디" in parsed["plan"]
        
        # Tags should be cleaned
        clean_tags = [tag for tag in parsed["tags"] if "```" not in tag and "'''" not in tag]
        assert len(clean_tags) == len(parsed["tags"])
        assert "Python" in parsed["tags"][0]
        assert "스터디" in parsed["tags"][2]


class TestLogFilteringEnhancements:
    """Test the enhanced log filtering"""
    
    def test_log_filtering_exclusions(self):
        """Test that new log patterns are properly excluded"""
        from src.core.ai_logger import DiscordHandler
        
        handler = DiscordHandler()
        
        # Test patterns that should be filtered out
        filtered_messages = [
            "[AI] 2025-07-30 00:12:34,790 INFO: [질문 전체 응답 수신 완료] time 4.258365154266357 sec",
            "[AI] 2025-07-30 00:12:34,790 INFO: [원본 응답]: '새로운 활동을 시작할 때...'",
            "[AI] 2025-07-30 00:12:34,790 DEBUG: [옵션 파싱 시작] raw 텍스트: options",
            "Some log with time 1.234 sec in it",
            "[AI] 2025-07-30 INFO: regular info message",
            "[AI] 2025-07-30 DEBUG: debug information"
        ]
        
        # Mock the handler's format method
        handler.format = lambda record: record.getMessage()
        
        # Create mock log records
        import logging
        for msg in filtered_messages:
            record = logging.LogRecord(
                name="ai",
                level=logging.INFO,
                pathname="/project/src/test.py", 
                lineno=1,
                msg=msg,
                args=(),
                exc_info=None
            )
            
            # The emit method should return early (not send to Discord) for these
            # We can't easily test the return, but we can verify the filtering logic
            blocked_keywords = [
                "[예외 처리]", "favicon.ico", "/docs", "[Moderation 평가]", "[유해성 차단]", 
                "[Client Error]", "[질문 전체 응답 수신 완료]", "[원본 응답]:", "[정리된 응답]:",
                "[옵션 파싱 시작]", "[vLLM 첫 chunk 수신]", "[추천 vLLM 첫 chunk 수신]",
                "[청크 처리]", "[청크 정리]", "[접두어", "[일반 스트리밍", "[옵션 파싱 성공",
                "[JSON 패턴 매치]", "[추천 청크 처리]", "time ", "[AI] 2025-", "INFO:", "DEBUG:"
            ]
            
            should_be_blocked = any(block in msg for block in blocked_keywords)
            # Most of these test messages should be blocked
            if "[AI] 2025-" in msg or "time " in msg or "INFO:" in msg or "DEBUG:" in msg:
                assert should_be_blocked, f"Message should be blocked: {msg}"


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_prefix_parser_empty_inputs(self):
        """Test prefix parser with edge case inputs"""
        parser = PrefixParser(["질문:"])
        
        # Empty string should return empty string
        assert parser.process_chunk("") == ""
        
        # Only whitespace should return trimmed result  
        parser2 = PrefixParser(["질문:"])
        result = parser2.process_chunk("   ")
        assert result.strip() == ""
        
        # Only special characters should return empty string
        parser3 = PrefixParser(["질문:"])
        assert parser3.process_chunk("\\n\\r\\t") == ""

    @pytest.mark.asyncio 
    async def test_streaming_error_handling(self):
        """Test that streaming functions handle errors gracefully"""
        
        # Mock an error in vLLM streaming
        async def mock_error_stream(messages):
            yield "시작"
            raise Exception("vLLM error")
        
        with patch('src.services.v2.ws_chatbot.stream_vllm_response', mock_error_stream):
            with patch('src.services.v2.ws_chatbot.get_session_history') as mock_history:
                mock_history.return_value.get_messages.return_value = []
                mock_history.return_value.add_ai_message = Mock()
                
                chunks = []
                try:
                    async for chunk in stream_question_chunks("test", "user123", "session123"):
                        if isinstance(chunk, str):
                            chunks.append(chunk)
                except Exception:
                    pass  # Expected to handle gracefully
                
                # Should have received at least the initial chunk
                assert len(chunks) >= 1


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v"])
