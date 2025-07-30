"""
Buffer parser utility to remove "이전 질문" (previous question) patterns from text buffers.
This helps clean up AI responses that echo back context information.
"""

import re
import logging
from typing import Optional, Tuple
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()


class BufferParser:
    """
    Utility class to parse and clean text buffers by removing unwanted patterns
    such as "이전 질문" (previous question) context repetition.
    """
    
    # Patterns to detect and remove "이전 질문" context
    PREVIOUS_QUESTION_PATTERNS = [
        r'이전\s*질문\s*[:：]\s*"[^"]*"',  # 이전 질문: "..."
        r'이전\s*질문\s*[:：]\s*\'[^\']*\'',  # 이전 질문: '...'
        r'이전\s*질문\s*[:：]\s*[^"\n]*',  # 이전 질문: (without quotes)
        r'Previous\s*question\s*[:：]\s*"[^"]*"',  # English version with "
        r'Previous\s*question\s*[:：]\s*\'[^\']*\'',  # English version with '
        r'Previous\s*question\s*[:：]\s*[^"\n]*',  # English without quotes
    ]
    
    # Patterns to detect user answer context
    USER_ANSWER_PATTERNS = [
        r'사용자\s*답변\s*[:：]\s*"[^"]*"',  # 사용자 답변: "..."
        r'사용자\s*답변\s*[:：]\s*\'[^\']*\'',  # 사용자 답변: '...'
        r'사용자\s*답변\s*[:：]\s*[^"\n]*',  # 사용자 답변: (without quotes)
        r'User\s*answer\s*[:：]\s*"[^"]*"',  # English version with "
        r'User\s*answer\s*[:：]\s*\'[^\']*\'',  # English version with '
        r'User\s*answer\s*[:：]\s*[^"\n]*',  # English without quotes
    ]
    
    # Combined context patterns
    CONTEXT_PATTERNS = PREVIOUS_QUESTION_PATTERNS + USER_ANSWER_PATTERNS
    
    # Separators that indicate end of context section
    CONTEXT_SEPARATORS = [
        r'\n\n+',  # Double newlines
        r'이\s*정보를\s*참고해',  # "이 정보를 참고해" (referencing this information)
        r'다음\s*질문을\s*생성',  # "다음 질문을 생성" (generate next question)
        r'질문을\s*만들어',  # "질문을 만들어" (create question)
    ]
    
    def __init__(self, max_context_length: int = 500):
        """
        Initialize buffer parser.
        
        Args:
            max_context_length: Maximum length of context section to process
        """
        self.max_context_length = max_context_length
        self.context_detected = False
        self.context_processed = False
        self.buffer = ""
        
    def detect_context_repetition(self, text: str) -> bool:
        """
        Detect if the text contains context repetition patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if context repetition is detected
        """
        for pattern in self.CONTEXT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                ai_logger.debug(f"[컨텍스트 감지] 패턴 매치: {pattern}")
                return True
        return False
        
    def find_context_separator(self, text: str) -> Optional[int]:
        """
        Find the position where context section ends.
        
        Args:
            text: Text to analyze
            
        Returns:
            Position of context separator, or None if not found
        """
        for pattern in self.CONTEXT_SEPARATORS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ai_logger.debug(f"[컨텍스트 분리자 발견] 패턴: {pattern}, 위치: {match.end()}")
                return match.end()
        return None
        
    def remove_context_patterns(self, text: str) -> str:
        """
        Remove context repetition patterns from text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text with context patterns removed
        """
        cleaned_text = text
        removed_patterns = []
        
        for pattern in self.CONTEXT_PATTERNS:
            matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
            if matches:
                removed_patterns.extend(matches)
                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
        
        if removed_patterns:
            ai_logger.info(f"[컨텍스트 패턴 제거됨] 제거된 패턴: {removed_patterns}")
        
        # Clean up extra whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
        
    def parse_streaming_chunk(self, chunk: str) -> Tuple[Optional[str], bool]:
        """
        Parse a streaming chunk and handle context detection/removal.
        
        Args:
            chunk: Incoming text chunk
            
        Returns:
            Tuple of (processed_chunk, context_found)
            - processed_chunk: None if chunk should be skipped, otherwise processed text
            - context_found: True if context was detected and handled
        """
        self.buffer += chunk
        
        # If we haven't detected context yet, check for it
        if not self.context_detected:
            if self.detect_context_repetition(self.buffer):
                self.context_detected = True
                ai_logger.info("[컨텍스트 반복 감지] AI가 컨텍스트를 반복 출력중")
        
        # If context was detected but not yet processed
        if self.context_detected and not self.context_processed:
            separator_pos = self.find_context_separator(self.buffer)
            
            if separator_pos:
                # Found separator, extract content after context
                actual_content = self.buffer[separator_pos:].strip()
                self.context_processed = True
                self.buffer = actual_content
                
                ai_logger.info("[컨텍스트 분리 완료] 실제 내용 추출됨")
                
                # Return the actual content if any
                if actual_content:
                    return actual_content, True
                else:
                    return None, True  # Skip this chunk, wait for more content
            else:
                # Still waiting for separator
                if len(self.buffer) > self.max_context_length:
                    # Buffer too long, assume no separator coming
                    ai_logger.warning("[컨텍스트 분리 포기] 버퍼가 너무 큼, 패턴 제거 시도")
                    cleaned = self.remove_context_patterns(self.buffer)
                    self.context_processed = True
                    self.buffer = cleaned
                    return cleaned if cleaned else None, True
                else:
                    # Continue waiting
                    return None, True
        
        # Context already processed or no context detected
        elif not self.context_detected:
            # No context detected, return chunk as-is
            return chunk, False
        else:
            # Context was processed, return chunk as-is
            return chunk, False
            
    def reset(self):
        """Reset the parser state for a new session."""
        self.context_detected = False
        self.context_processed = False
        self.buffer = ""
        ai_logger.debug("[버퍼 파서 리셋] 새 세션 시작")


def remove_previous_question_from_text(text: str) -> str:
    """
    Utility function to remove "이전 질문" patterns from any text.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    parser = BufferParser()
    return parser.remove_context_patterns(text)


def clean_prompt_context(prompt: str) -> str:
    """
    Clean a prompt by removing context repetition while preserving the instruction parts.
    
    Args:
        prompt: Original prompt text
        
    Returns:
        Cleaned prompt
    """
    # Split prompt into lines and analyze
    lines = prompt.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip lines that contain context patterns
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in BufferParser.CONTEXT_PATTERNS):
            ai_logger.debug(f"[프롬프트 정리] 컨텍스트 라인 제거: {line[:50]}...")
            continue
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


# Example usage patterns for logging
EXAMPLE_PATTERNS = [
    '이전 질문: "어떤 활동을 선호하시나요?"',
    '사용자 답변: "운동을 좋아합니다"',
    'Previous question: "What activities do you prefer?"',
    'User answer: "I like sports"',
]

if __name__ == "__main__":
    # Test the parser with example patterns
    parser = BufferParser()
    
    test_text = """
    이전 질문: "어떤 모임을 선호하시나요?"
    사용자 답변: "운동 모임을 좋아합니다"
    
    이 정보를 참고해서 다음 질문을 생성하겠습니다.
    
    그렇다면 어떤 종류의 운동을 선호하시나요?
    """
    
    print("Original text:")
    print(test_text)
    print("\nCleaned text:")
    print(remove_previous_question_from_text(test_text))
