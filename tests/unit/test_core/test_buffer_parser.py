"""
BufferParser 테스트 모듈
"""

import pytest
from app.core.buffer_parser import (
    BufferParser, 
    clean_prompt_context, 
    remove_previous_question_from_text,
    detect_context_repetition,
    is_context_repetition,
    extract_clean_content
)

class TestBufferParser:
    """BufferParser 클래스 테스트"""
    
    def test_init(self):
        """초기화 테스트"""
        parser = BufferParser()
        assert parser.buffer == ""
        assert not parser.context_detected
        assert not parser.clean_content_started
        assert parser.separator == "\n\n"
    
    def test_no_context_detection(self):
        """컨텍스트가 없는 경우 테스트"""
        parser = BufferParser()
        
        chunks = ["안녕하세요!", " 추천해드릴", " 모임이 있습니다."]
        results = []
        
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            results.append(result)
        
        assert results == ["안녕하세요!", " 추천해드릴", " 모임이 있습니다."]
        assert not parser.context_detected
    
    def test_context_detection_with_separator(self):
        """컨텍스트 감지 및 구분자 처리 테스트"""
        parser = BufferParser()
        
        chunks = ["이전 질문:", " 사용자가", " 풋살에", " 대해 물어봤습니다.", "\n\n", "안녕하세요!", " 추천해드릴", " 모임이 있습니다."]
        results = []
        
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            results.append(result)
        
        # 처음 4개 청크는 컨텍스트이므로 빈 문자열
        assert results[:4] == ["", "", "", ""]
        # 구분자 이후 첫 번째 청크는 깨끗한 콘텐츠
        assert results[4] == ""  # 구분자 자체
        assert results[5] == "안녕하세요!"  # 첫 깨끗한 콘텐츠
        # 이후 청크들은 그대로 반환
        assert results[6:] == [" 추천해드릴", " 모임이 있습니다."]
        
        assert parser.context_detected
        assert parser.clean_content_started
    
    def test_get_clean_content(self):
        """깨끗한 콘텐츠 추출 테스트"""
        parser = BufferParser()
        
        # 컨텍스트가 없는 경우
        parser.buffer = "안녕하세요! 추천해드릴 모임이 있습니다."
        assert parser.get_clean_content() == "안녕하세요! 추천해드릴 모임이 있습니다."
        
        # 컨텍스트가 있는 경우
        parser.reset()
        parser.buffer = "이전 질문: 사용자가 풋살에 대해 물어봤습니다.\n\n안녕하세요! 추천해드릴 모임이 있습니다."
        parser.context_detected = True
        assert parser.get_clean_content() == "안녕하세요! 추천해드릴 모임이 있습니다."
    
    def test_reset(self):
        """파서 리셋 테스트"""
        parser = BufferParser()
        parser.buffer = "테스트"
        parser.context_detected = True
        parser.clean_content_started = True
        
        parser.reset()
        
        assert parser.buffer == ""
        assert not parser.context_detected
        assert not parser.clean_content_started

class TestCleanPromptContext:
    """clean_prompt_context 함수 테스트"""
    
    def test_no_context(self):
        """컨텍스트가 없는 경우"""
        text = "안녕하세요! 추천해드릴 모임이 있습니다."
        result = clean_prompt_context(text)
        assert result == text
    
    def test_previous_question_context(self):
        """이전 질문 컨텍스트 제거"""
        text = "이전 질문: 사용자가 풋살에 대해 물어봤습니다.\n\n안녕하세요! 추천해드릴 모임이 있습니다."
        result = clean_prompt_context(text)
        assert result == "안녕하세요! 추천해드릴 모임이 있습니다."
    
    def test_multiple_contexts(self):
        """여러 컨텍스트 패턴 제거"""
        text = """이전 질문: 사용자가 풋살에 대해 물어봤습니다.
사용자 답변: 네, 풋살을 하고 싶어요.

안녕하세요! 추천해드릴 모임이 있습니다."""
        result = clean_prompt_context(text)
        assert result == "안녕하세요! 추천해드릴 모임이 있습니다."
    
    def test_empty_text(self):
        """빈 텍스트 처리"""
        assert clean_prompt_context("") == ""
        assert clean_prompt_context(None) == None

class TestRemovePreviousQuestion:
    """remove_previous_question_from_text 함수 테스트"""
    
    def test_remove_previous_question(self):
        """이전 질문 제거 테스트"""
        text = "이전 질문: 사용자가 풋살에 대해 물어봤습니다.\n\n안녕하세요!"
        result = remove_previous_question_from_text(text)
        assert result == "안녕하세요!"
    
    def test_no_previous_question(self):
        """이전 질문이 없는 경우"""
        text = "안녕하세요! 추천해드릴 모임이 있습니다."
        result = remove_previous_question_from_text(text)
        assert result == text
    
    def test_empty_text(self):
        """빈 텍스트 처리"""
        assert remove_previous_question_from_text("") == ""

class TestDetectContextRepetition:
    """detect_context_repetition 함수 테스트"""
    
    def test_no_context_repetition(self):
        """컨텍스트 반복이 없는 경우"""
        text = "안녕하세요! 추천해드릴 모임이 있습니다."
        result = detect_context_repetition(text)
        
        assert not result["has_context_repetition"]
        assert result["detected_patterns"] == []
        assert result["clean_content_start"] == 0
        assert result["original_length"] == len(text)
        assert result["clean_length"] == len(text)
    
    def test_context_repetition_detected(self):
        """컨텍스트 반복 감지"""
        text = "이전 질문: 사용자가 풋살에 대해 물어봤습니다.\n\n안녕하세요!"
        result = detect_context_repetition(text)
        
        assert result["has_context_repetition"]
        assert "previous_question" in result["detected_patterns"]
        assert result["clean_content_start"] > 0
        assert result["clean_length"] == len("안녕하세요!")
    
    def test_multiple_patterns(self):
        """여러 패턴 감지"""
        text = """이전 질문: 테스트
사용자 답변: 네

안녕하세요!"""
        result = detect_context_repetition(text)
        
        assert result["has_context_repetition"]
        assert "previous_question" in result["detected_patterns"]
        assert "user_answer" in result["detected_patterns"]

class TestConvenienceFunctions:
    """편의 함수들 테스트"""
    
    def test_is_context_repetition(self):
        """is_context_repetition 함수 테스트"""
        assert not is_context_repetition("안녕하세요!")
        assert is_context_repetition("이전 질문: 테스트\n\n안녕하세요!")
    
    def test_extract_clean_content(self):
        """extract_clean_content 함수 테스트"""
        text_with_context = "이전 질문: 테스트\n\n안녕하세요!"
        text_without_context = "안녕하세요!"
        
        assert extract_clean_content(text_with_context) == "안녕하세요!"
        assert extract_clean_content(text_without_context) == "안녕하세요!"

class TestEdgeCases:
    """엣지 케이스 테스트"""
    
    def test_context_without_separator(self):
        """구분자 없이 컨텍스트만 있는 경우"""
        parser = BufferParser()
        chunks = ["이전 질문:", " 테스트"]
        
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            assert result == ""  # 구분자가 없으므로 빈 문자열
        
        assert parser.context_detected
        assert not parser.clean_content_started
    
    def test_separator_without_context(self):
        """컨텍스트 없이 구분자만 있는 경우"""
        parser = BufferParser()
        chunks = ["안녕하세요", "\n\n", "반갑습니다"]
        results = []
        
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            results.append(result)
        
        assert results == ["안녕하세요", "\n\n", "반갑습니다"]
        assert not parser.context_detected
    
    def test_mixed_case_patterns(self):
        """대소문자 혼합 패턴 테스트"""
        text = "이전 질문: 테스트\n\n안녕하세요!"
        result = clean_prompt_context(text)
        assert result == "안녕하세요!"
        
        text_upper = "이전 질문: 테스트\n\n안녕하세요!"
        result_upper = clean_prompt_context(text_upper)
        assert result_upper == "안녕하세요!"
    
    def test_whitespace_handling(self):
        """공백 처리 테스트"""
        text = "이전 질문 :   테스트   \n\n   안녕하세요!   "
        result = clean_prompt_context(text)
        assert result == "안녕하세요!"
    
    def test_multiple_separators(self):
        """여러 구분자 처리"""
        text = "이전 질문: 테스트\n\n\n\n안녕하세요!"
        result = clean_prompt_context(text)
        assert result == "안녕하세요!"

if __name__ == "__main__":
    pytest.main([__file__])
