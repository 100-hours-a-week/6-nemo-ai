"""
BufferParser: 컨텍스트 반복 제거 및 스트리밍 텍스트 처리
AI 응답에서 "이전 질문", "사용자 답변" 등의 반복적인 컨텍스트를 감지하고 제거합니다.
"""

import re
from typing import Optional, Dict, Any
from app.core.ai_logger import get_ai_logger

logger = get_ai_logger()

class BufferParser:
    """스트리밍 텍스트에서 컨텍스트 반복을 감지하고 제거하는 클래스"""
    
    def __init__(self):
        self.buffer = ""
        self.context_patterns = [
            r'이전\s*질문\s*:\s*',
            r'사용자\s*답변\s*:\s*',
            r'사용자\s*질문\s*:\s*',
            r'컨텍스트\s*:\s*',
            r'질문\s*:\s*',
            r'답변\s*:\s*'
        ]
        self.context_detected = False
        self.clean_content_started = False
        self.separator = "\n\n"
        
    def process_chunk(self, chunk: str) -> str:
        """
        스트리밍 청크를 처리하여 컨텍스트 반복을 제거
        
        Args:
            chunk: 새로 들어온 텍스트 청크
            
        Returns:
            처리된 텍스트 (컨텍스트가 감지되면 빈 문자열 반환)
        """
        self.buffer += chunk
        
        # 컨텍스트 패턴 감지
        if not self.context_detected:
            for pattern in self.context_patterns:
                if re.search(pattern, self.buffer, re.IGNORECASE):
                    self.context_detected = True
                    logger.debug(f"[BufferParser] 컨텍스트 패턴 감지: {pattern}")
                    break
        
        # 컨텍스트가 감지되었고 아직 깨끗한 콘텐츠가 시작되지 않았다면
        if self.context_detected and not self.clean_content_started:
            # 구분자를 찾아서 깨끗한 콘텐츠 시작점 확인
            if self.separator in self.buffer:
                separator_index = self.buffer.find(self.separator)
                # 구분자 이후의 내용만 깨끗한 콘텐츠로 처리
                clean_start = separator_index + len(self.separator)
                clean_content = self.buffer[clean_start:].strip()
                
                if clean_content:
                    self.clean_content_started = True
                    logger.debug(f"[BufferParser] 깨끗한 콘텐츠 시작 감지")
                    return clean_content
                    
            return ""  # 아직 깨끗한 콘텐츠가 시작되지 않음
        
        # 깨끗한 콘텐츠가 이미 시작되었거나 컨텍스트가 감지되지 않은 경우
        if not self.context_detected or self.clean_content_started:
            # 새로운 청크만 반환 (이미 처리된 버퍼 내용 제외)
            if self.clean_content_started:
                # 이미 처리된 내용을 제외하고 새 청크만 반환
                return chunk
            else:
                # 컨텍스트가 감지되지 않은 경우 전체 청크 반환
                return chunk
        
        return ""
    
    def get_clean_content(self) -> str:
        """버퍼에서 깨끗한 콘텐츠만 추출"""
        if not self.context_detected:
            return self.buffer.strip()
        
        if self.separator in self.buffer:
            separator_index = self.buffer.find(self.separator)
            clean_start = separator_index + len(self.separator)
            return self.buffer[clean_start:].strip()
        
        return ""
    
    def reset(self):
        """파서 상태 초기화"""
        self.buffer = ""
        self.context_detected = False
        self.clean_content_started = False

def clean_prompt_context(text: str) -> str:
    """
    완성된 텍스트에서 컨텍스트 반복을 제거
    
    Args:
        text: 처리할 텍스트
        
    Returns:
        컨텍스트가 제거된 깨끗한 텍스트
    """
    if not text:
        return text
    
    # 컨텍스트 패턴들
    context_patterns = [
        r'이전\s*질문\s*:\s*.*?(?=\n\n|\Z)',
        r'사용자\s*답변\s*:\s*.*?(?=\n\n|\Z)',
        r'사용자\s*질문\s*:\s*.*?(?=\n\n|\Z)',
        r'컨텍스트\s*:\s*.*?(?=\n\n|\Z)',
        r'질문\s*:\s*.*?(?=\n\n|\Z)',
        r'답변\s*:\s*.*?(?=\n\n|\Z)'
    ]
    
    cleaned_text = text
    
    # 각 패턴에 대해 제거 수행
    for pattern in context_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.DOTALL)
    
    # 연속된 줄바꿈 정리
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
    cleaned_text = cleaned_text.strip()
    
    if cleaned_text != text:
        logger.debug(f"[BufferParser] 컨텍스트 정리 완료: {len(text)} -> {len(cleaned_text)} chars")
    
    return cleaned_text

def remove_previous_question_from_text(text: str) -> str:
    """
    텍스트에서 "이전 질문" 부분을 감지하고 제거
    
    Args:
        text: 처리할 텍스트
        
    Returns:
        이전 질문이 제거된 텍스트
    """
    if not text:
        return text
    
    # "이전 질문:" 패턴과 그 이후 내용을 찾아서 제거
    pattern = r'이전\s*질문\s*:.*?(?=\n\n|$)'
    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # 불필요한 공백과 줄바꿈 정리
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned).strip()
    
    return cleaned

def detect_context_repetition(text: str) -> Dict[str, Any]:
    """
    텍스트에서 컨텍스트 반복을 감지하고 분석 결과 반환
    
    Args:
        text: 분석할 텍스트
        
    Returns:
        감지 결과 딕셔너리
    """
    result = {
        "has_context_repetition": False,
        "detected_patterns": [],
        "clean_content_start": 0,
        "original_length": len(text),
        "clean_length": 0
    }
    
    patterns = {
        "previous_question": r'이전\s*질문\s*:\s*',
        "user_answer": r'사용자\s*답변\s*:\s*',
        "user_question": r'사용자\s*질문\s*:\s*',
        "context": r'컨텍스트\s*:\s*',
        "question": r'질문\s*:\s*',
        "answer": r'답변\s*:\s*'
    }
    
    # 각 패턴 감지
    for pattern_name, pattern in patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            result["has_context_repetition"] = True
            result["detected_patterns"].append(pattern_name)
    
    # 깨끗한 콘텐츠 시작점 찾기
    if result["has_context_repetition"]:
        separator_match = re.search(r'\n\n', text)
        if separator_match:
            result["clean_content_start"] = separator_match.end()
            clean_content = text[result["clean_content_start"]:].strip()
            result["clean_length"] = len(clean_content)
    else:
        result["clean_length"] = result["original_length"]
    
    return result

# 편의 함수들
def is_context_repetition(text: str) -> bool:
    """텍스트에 컨텍스트 반복이 있는지 간단히 확인"""
    return detect_context_repetition(text)["has_context_repetition"]

def extract_clean_content(text: str) -> str:
    """텍스트에서 깨끗한 콘텐츠만 추출"""
    detection = detect_context_repetition(text)
    if detection["has_context_repetition"] and detection["clean_content_start"] > 0:
        return text[detection["clean_content_start"]:].strip()
    return text.strip()

if __name__ == "__main__":
    # 테스트 코드
    test_text = """이전 질문: 사용자가 풋살에 대해 물어봤습니다.
사용자 답변: 네, 풋살을 하고 싶어요.

안녕하세요! 풋살 모임을 찾고 계시는군요. 추천해드릴 모임이 있습니다."""
    
    print("=== BufferParser 테스트 ===")
    print("원본 텍스트:")
    print(repr(test_text))
    print()
    
    # 컨텍스트 감지 테스트
    detection = detect_context_repetition(test_text)
    print("감지 결과:", detection)
    print()
    
    # 정리된 텍스트
    cleaned = clean_prompt_context(test_text)
    print("정리된 텍스트:")
    print(repr(cleaned))
    print()
    
    # 스트리밍 테스트
    print("=== 스트리밍 테스트 ===")
    parser = BufferParser()
    chunks = ["이전 질문:", " 사용자가", " 풋살에", " 대해 물어봤습니다.", "\n\n", "안녕하세요!", " 추천해드릴", " 모임이 있습니다."]
    
    for i, chunk in enumerate(chunks):
        result = parser.process_chunk(chunk)
        print(f"청크 {i+1}: {repr(chunk)} -> {repr(result)}")
