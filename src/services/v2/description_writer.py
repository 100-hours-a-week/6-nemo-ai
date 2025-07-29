from typing import Tuple
from src.schemas.v1.group_writer import GroupGenerationRequest
from src.core.ai_logger import get_ai_logger
from src.models.gemma_3_4b import call_vllm_api
import re
import httpx
from src.config import vLLM_URL, VLLM_TIMEOUT, VLLM_READ_TIMEOUT

ai_logger = get_ai_logger()


async def _call_vllm_for_description(prompt: str) -> str:
    """
    Specialized VLLM call ONLY for description generation
    Uses optimized parameters without affecting global VLLM behavior
    """
    VLLM_API_URL = f"{vLLM_URL.rstrip('/')}/v1/completions"
    
    # Specialized parameters ONLY for description generation
    payload = {
        "prompt": prompt,
        "max_tokens": 300,  # Reduced to prevent over-generation
        "temperature": 0.4,  # Lower for focused output
        "top_p": 0.9,
        "frequency_penalty": 0.5,  # Reduce repetition
        "presence_penalty": 0.3,
        "stop": ["한 줄 소개:", "상세 설명:", "\n\n\n", "Step"],  # Stop tokens specific to descriptions
        "repetition_penalty": 1.1,
    }
    
    timeout_config = httpx.Timeout(
        connect=10.0,
        read=VLLM_READ_TIMEOUT,
        write=10.0,
        pool=VLLM_TIMEOUT
    )
    
    try:
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(VLLM_API_URL, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("text", "").strip()
    except Exception as e:
        ai_logger.warning(f"[Description VLLM] Specialized call failed: {e}")
        # Fallback to regular call if specialized fails
        return await call_vllm_api(prompt, max_tokens=300, temperature=0.4)


def _remove_repetitive_content(text: str) -> str:
    """Remove repetitive sentences and phrases from text"""
    if not text:
        return text
    
    # Split into sentences
    sentences = [s.strip() for s in re.split(r'[.。!]', text) if s.strip()]
    
    # Remove duplicate sentences (exact matches)
    unique_sentences = []
    seen_sentences = set()
    
    for sentence in sentences:
        # Normalize sentence for comparison (remove extra spaces, punctuation)
        normalized = re.sub(r'[^\w가-힣]', '', sentence).lower()
        if normalized and normalized not in seen_sentences and len(normalized) > 3:
            seen_sentences.add(normalized)
            unique_sentences.append(sentence)
    
    # Check for repetitive phrases within sentences
    cleaned_sentences = []
    for sentence in unique_sentences:
        # Remove repetitive phrase patterns
        cleaned_sentence = _remove_phrase_repetition(sentence)
        if cleaned_sentence and len(cleaned_sentence.strip()) > 5:
            cleaned_sentences.append(cleaned_sentence)
    
    result = '. '.join(cleaned_sentences)
    if result and not result.endswith('.'):
        result += '.'
    
    return result


def _remove_phrase_repetition(text: str) -> str:
    """Remove repetitive phrases within a single text"""
    if not text:
        return text
    
    # Common repetitive patterns in Korean group descriptions
    repetitive_patterns = [
        r'(- [^-\n]+)(\1){2,}',  # Repeated bullet points
        r'(다양한\s+[가-힣]+과?\s*)(\1){2,}',  # Repeated "다양한 X와" patterns
        r'(새로운\s+[가-힣]+과?\s*)(\1){2,}',  # Repeated "새로운 X와" patterns
        r'(편안하고\s+즐거운\s+[가-힣]+\s*)(\1){2,}',  # Repeated mood descriptions
        r'(함께\s+[가-힣]+\s*)(\1){2,}',  # Repeated "함께 X" patterns
    ]
    
    cleaned_text = text
    for pattern in repetitive_patterns:
        cleaned_text = re.sub(pattern, r'\1', cleaned_text, flags=re.IGNORECASE)
    
    return cleaned_text


def _is_description_corrupted(text: str) -> bool:
    """Check if description text is corrupted - SPECIFIC to group descriptions"""
    if not text or not isinstance(text, str):
        return True
    
    text = text.strip()
    if len(text) < 3:
        return True
    
    # Patterns specific to group description corruption
    corruption_patterns = [
        r'만남을$',  # Your specific truncation pattern
        r'[가-힣]{1,2}을$',  # General Korean truncation
        r'(다양한|새로운|편안하고|즐거운).*(\1.*){3,}',  # Excessive repetition of descriptive words
        r'[가-힣]+[0-9]+[가-힣]*',  # Korean mixed with numbers
        r'(?:은|가|이|를|에|의){3,}',  # Repeated particles
    ]
    
    for pattern in corruption_patterns:
        if re.search(pattern, text):
            return True
    
    # Check for incomplete Korean sentences
    if len(text) > 10 and not re.search(r'[다요니까습니다음겠앙함면동]$', text):
        return True
    
    # Check for excessive word repetition (specific to descriptions)
    words = text.split()
    if len(words) > 10:
        word_count = {}
        for word in words:
            if len(word) > 2:  # Skip particles and short words
                word_count[word] = word_count.get(word, 0) + 1
        
        # If any meaningful word appears more than 25% of the time, likely repetitive
        max_count = max(word_count.values()) if word_count else 0
        if max_count > len(words) * 0.25:
            return True
    
    return False


def _clean_description_artifacts(text: str) -> str:
    """Clean description-specific artifacts"""
    if not text:
        return text
    
    # Remove format indicators specific to descriptions
    text = re.sub(r'한 줄 소개:\s*', '', text)
    text = re.sub(r'상세 설명:\s*', '', text)
    
    # Clean up mixed Korean-Latin artifacts
    text = re.sub(r'[가-힣]+[a-zA-Z0-9]+[가-힣]*', '', text)
    
    # Fix spacing
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove incomplete sentences at the end (specific to descriptions)
    if not re.search(r'[다요니까습니다음겠앙함면동]$', text):
        # Find last complete sentence
        sentences = re.split(r'[.。!]', text)
        complete_sentences = []
        for sentence in sentences[:-1]:  # Exclude last potentially incomplete sentence
            if sentence.strip() and re.search(r'[다요니까습니다음겠앙함면동]', sentence):
                complete_sentences.append(sentence.strip())
        
        if complete_sentences:
            text = '. '.join(complete_sentences) + '.'
    
    return text


def _get_fallback_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    """Generate clean fallback description"""
    category_descriptions = {
        "스터디": "함께 학습하며 성장하는 스터디 모임",
        "취미": "공통 취미를 즐기며 소통하는 취미 모임", 
        "친목": "친목을 도모하며 즐거운 시간을 보내는 모임",
        "운동": "건강한 운동을 함께하는 활동적인 모임",
        "문화": "다양한 문화 활동을 공유하는 문화 모임"
    }
    
    # Generate basic summary
    category_key = next((key for key in category_descriptions.keys() if key in data.category), "친목")
    summary = category_descriptions.get(category_key, "다양한 활동을 함께하는 모임")
    
    # Generate focused description (avoid repetition)
    description = f"이 모임은 {data.goal}을 목적으로 합니다. {data.period} 동안 진행되며, 관심있는 분들의 참여를 환영합니다. 함께 즐거운 시간을 보내며 좋은 인연을 만들어보세요."
    
    return summary, description


def _parse_alternative_format(response: str, data: GroupGenerationRequest) -> Tuple[str, str]:
    """Try alternative parsing when standard format fails"""
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    
    summary = ""
    description = ""
    
    for i, line in enumerate(lines):
        if not summary and len(line) < 50 and ("모임" in line or "스터디" in line or "동아리" in line):
            summary = line
        elif not description and len(line) > 30:
            description = line
            # Try to get more description from following lines
            if i + 1 < len(lines):
                next_lines = lines[i+1:i+3]
                for next_line in next_lines:
                    if len(next_line) > 10 and not _is_description_corrupted(next_line):
                        description += " " + next_line
            break
    
    # Fallback if parsing still fails
    if not summary or not description or _is_description_corrupted(summary) or _is_description_corrupted(description):
        return _get_fallback_description(data)
    
    return summary, description


async def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    """Enhanced description generation with targeted repetition prevention"""
    
    prompt = f"""다음 정보를 바탕으로 모임 소개를 작성하세요.

요구사항:
1. 한 줄 소개: 50자 이내의 간단한 설명 (명사로 끝나야 함)
2. 상세 설명: 200자 이내의 자연스러운 설명
3. 같은 내용을 반복하지 마세요
4. 완전한 문장으로만 작성하세요

모임 정보:
- 이름: {data.name}
- 목적: {data.goal}
- 분야: {data.category}
- 기간: {data.period}

출력 형식:
한 줄 소개: [간단한 설명]
상세 설명: [자세한 설명]

한 줄 소개:"""

    try:
        ai_logger.info("[AI-v2] [요약 생성 시작]", extra={"meeting_name": data.name})

        # Use specialized VLLM call for descriptions
        response = await _call_vllm_for_description(prompt)
        
        if not response or _is_description_corrupted(response):
            ai_logger.warning("[AI-v2] [텍스트 손상 감지] 폴백 사용")
            return _get_fallback_description(data)
        
        # Parse response
        parts = response.split("한 줄 소개:")
        if len(parts) < 2:
            ai_logger.warning("[AI-v2] [파싱 실패] 형식 불일치")
            return _parse_alternative_format(response, data)

        after_intro = parts[1]
        subparts = after_intro.split("상세 설명:")
        if len(subparts) < 2:
            ai_logger.warning("[AI-v2] [파싱 실패] 상세 설명 없음")
            return _parse_alternative_format(response, data)

        summary = subparts[0].strip()
        description = subparts[1].strip()
        
        # Clean and validate
        summary = _clean_description_artifacts(summary)
        description = _clean_description_artifacts(description)
        
        # Remove repetitive content (ONLY for descriptions)
        description = _remove_repetitive_content(description)
        
        # Final validation
        if (_is_description_corrupted(summary) or _is_description_corrupted(description) or 
            len(summary) < 3 or len(description) < 10):
            ai_logger.warning("[AI-v2] [최종 검증 실패] 폴백 사용")
            return _get_fallback_description(data)

        # Ensure proper length limits
        if len(summary) > 80:
            summary = summary[:77] + "..."
        if len(description) > 400:
            description = description[:397] + "..."

        ai_logger.info("[AI-v2] [모임 소개 생성 완료]", 
                      extra={
                          "summary_length": len(summary), 
                          "description_length": len(description)
                      })
        
        return summary, description

    except Exception as e:
        ai_logger.exception("[AI-v2] [생성 실패]")
        return _get_fallback_description(data)


if __name__ == "__main__":
    import asyncio
    from src.schemas.v1.group_writer import GroupGenerationRequest

    data = GroupGenerationRequest(
        name="로미의 백반기행",
        goal="판교의 맛집과 분좋카를 찾아 다니며 즐기는 친목 모임",
        category="친목/사교",
        period="3개월",
        isPlanCreated=False
    )


    async def run_test():
        summary, description = await generate_description(data)
        print("\n한 줄 소개:\n", summary)
        print("\n상세 설명:\n", description)


    asyncio.run(run_test())
