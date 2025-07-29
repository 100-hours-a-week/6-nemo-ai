"""
Retry handler and content validator for AI-generated content
Ensures quality and prevents PII/irrelevant content from being returned
"""

import asyncio
import re
from typing import List, Optional, Tuple, Any, Callable
from app.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

class ContentValidator:
    """Validates and cleans AI-generated content"""
    
    # PII and sensitive information patterns
    PII_PATTERNS = [
        r'\b\d{2,3}-\d{3,4}-\d{4}\b',  # Phone numbers
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # Email addresses
        r'\b\d{3}-\d{2}-\d{5}\b',  # Registration numbers
        r'\bhttps?://[^\s]+',  # URLs
        r'\b\d{5}-\d{5}\b',  # Postal codes
        r'\b\d{2}:\d{2}\b',  # Time patterns
        r'\b\d{4}\.\d{2}\.\d{2}\b',  # Date patterns
        r'\b[0-9,]+원\b',  # Money amounts
        r'\b담당자[:\s]*[가-힣]{2,4}\b',  # Contact person names
        r'\b문의[:\s]*\([0-9-]+\)',  # Contact inquiry
        r'\b\[REDACTED\]',  # Already redacted content
    ]
    
    # Irrelevant content indicators
    IRRELEVANT_PATTERNS = [
        r'한국건설기술인협회',
        r'건설워크넷',
        r'건설\s*분야',
        r'프로젝트비',
        r'보고서\s*형태',
        r'전문가\s*자문',
        r'팀\s*연구',
        r'성과\s*지표',
        r'기대\s*효과',
        r'홈페이지',
        r'이메일',
        r'담당자',
        r'참고사항',
        r'본\s*프로젝트는',
        r'외부\s*전문가',
    ]
    
    @classmethod
    def is_empty_or_invalid(cls, text: str) -> bool:
        """Check if text is empty or invalid"""
        if not text or not isinstance(text, str):
            return True
        
        text = text.strip()
        if len(text) < 3:
            return True
            
        # Check for placeholder values (but NOT "string" since that's a valid meeting name)
        if text.lower() in ['none', 'null', 'undefined', '']:
            return True
            
        return False
    
    @classmethod
    def contains_pii(cls, text: str) -> bool:
        """Check if text contains PII or sensitive information"""
        if not text:
            return False
            
        for pattern in cls.PII_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def contains_irrelevant_content(cls, text: str, topic_context: str = "") -> bool:
        """Check if text contains irrelevant content based on context"""
        if not text:
            return False
            
        # If topic context doesn't match construction but content is about construction
        if topic_context and "건설" not in topic_context.lower():
            for pattern in cls.IRRELEVANT_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        return False
    
    @classmethod
    def clean_content(cls, text: str, topic_context: str = "") -> str:
        """Clean content by removing PII and irrelevant information"""
        if not text:
            return text
            
        cleaned_text = text
        
        # Remove PII patterns
        for pattern in cls.PII_PATTERNS:
            cleaned_text = re.sub(pattern, '[정보삭제]', cleaned_text, flags=re.IGNORECASE)
        
        # Remove irrelevant sentences if topic doesn't match
        if topic_context and "건설" not in topic_context.lower():
            sentences = re.split(r'[.!?]\s*', cleaned_text)
            relevant_sentences = []
            
            for sentence in sentences:
                is_irrelevant = any(
                    re.search(pattern, sentence, re.IGNORECASE) 
                    for pattern in cls.IRRELEVANT_PATTERNS
                )
                if not is_irrelevant and sentence.strip():
                    relevant_sentences.append(sentence.strip())
            
            if relevant_sentences:
                cleaned_text = '. '.join(relevant_sentences)
                if not cleaned_text.endswith('.'):
                    cleaned_text += '.'
        
        # Clean up multiple spaces and normalize
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
    
    @classmethod
    def validate_meeting_data(cls, name: str, summary: str, description: str, tags: List[str], topic_context: str = "") -> Tuple[bool, List[str]]:
        """Validate all meeting data fields"""
        issues = []
        
        # Check for empty required fields
        if cls.is_empty_or_invalid(name):
            issues.append("Name is empty or invalid")
        if cls.is_empty_or_invalid(summary):
            issues.append("Summary is empty or invalid")
        if cls.is_empty_or_invalid(description):
            issues.append("Description is empty or invalid")
        if not tags or len(tags) == 0:
            issues.append("Tags list is empty")
        
        # Check for PII in content
        if summary and cls.contains_pii(summary):
            issues.append("Summary contains PII")
        if description and cls.contains_pii(description):
            issues.append("Description contains PII")
        
        # Check for irrelevant content
        if summary and cls.contains_irrelevant_content(summary, topic_context):
            issues.append("Summary contains irrelevant content")
        if description and cls.contains_irrelevant_content(description, topic_context):
            issues.append("Description contains irrelevant content")
        
        # Check for minimum content quality
        if summary and len(summary.strip()) < 10:
            issues.append("Summary too short")
        if description and len(description.strip()) < 20:
            issues.append("Description too short")
            
        # Check for maximum reasonable lengths
        if summary and len(summary.strip()) > 200:
            issues.append("Summary too long")
        if description and len(description.strip()) > 1000:
            issues.append("Description too long")
        
        # Check tags quality
        if tags:
            for tag in tags:
                if cls.contains_pii(tag):
                    issues.append(f"Tag contains PII: {tag}")
                if cls.contains_irrelevant_content(tag, topic_context):
                    issues.append(f"Tag contains irrelevant content: {tag}")
        
        return len(issues) == 0, issues


class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def retry_with_validation(
        self,
        operation: Callable,
        validator: Callable[[Any], Tuple[bool, List[str]]],
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Retry operation with validation"""
        
        last_exception = None
        last_validation_issues = []
        
        for attempt in range(self.max_retries):
            try:
                ai_logger.info(f"[RETRY] {operation_name} attempt {attempt + 1}/{self.max_retries}")
                
                # Execute operation
                result = await operation(*args, **kwargs)
                
                # Validate result
                is_valid, issues = validator(result)
                
                if is_valid:
                    ai_logger.info(f"[RETRY] {operation_name} succeeded on attempt {attempt + 1}")
                    return result
                else:
                    last_validation_issues = issues
                    ai_logger.warning(f"[RETRY] {operation_name} validation failed on attempt {attempt + 1}: {issues}")
                    
                    # Wait before retry (exponential backoff)
                    if attempt < self.max_retries - 1:
                        delay = self.base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        
            except Exception as e:
                last_exception = e
                ai_logger.error(f"[RETRY] {operation_name} failed on attempt {attempt + 1}: {str(e)}")
                
                # Wait before retry
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        # All retries failed
        error_msg = f"All {self.max_retries} attempts failed for {operation_name}"
        if last_validation_issues:
            error_msg += f". Last validation issues: {last_validation_issues}"
        if last_exception:
            error_msg += f". Last exception: {str(last_exception)}"
            
        ai_logger.error(error_msg)
        raise Exception(error_msg)
