from typing import Tuple
from src.schemas.v1.group_writer import GroupGenerationRequest
# from src.core.cloud_logging import logger
from src.core.ai_logger import get_ai_logger
from src.models.gemma_3_4b import call_vllm_api   #로컬 모델 호출로 교체
import re

ai_logger = get_ai_logger()


def _is_text_corrupted(text: str) -> bool:
    """Check if text appears corrupted or garbled"""
    if not text or not isinstance(text, str):
        return True
    
    text = text.strip()
    if len(text) < 3:
        return True
    
    # Check for patterns indicating corruption
    corruption_patterns = [
        r'할로운 분위기',  # Specific corruption pattern from your assessment
        r'교류하고율',     # Another specific pattern
        r'영n',           # Truncated pattern
        r'[가-힣]+[0-9]+[가-힣]*',  # Korean mixed with numbers inappropriately
        r'[?]{2,}',       # Multiple question marks
        r'(?:은|가|이|를|에|의){3,}',  # Repeated particles
        r'[가-힣]n$',     # Korean ending with 'n' (truncation indicator)
    ]
    
    for pattern in corruption_patterns:
        if re.search(pattern, text):
            return True
    
    # Check for incomplete sentences (Korean text ending abruptly)
    if len(text) > 10 and not text[-1] in '다요니까습음겠앙함면동':
        # Ends with incomplete syllables or weird characters
        if re.search(r'[가-힣][a-zA-Z0-9]$', text):
            return True
    
    return False


def _clean_text_artifacts(text: str) -> str:
    """Clean up any text artifacts or formatting issues"""
    if not text:
        return text
    
    # Remove any remaining format indicators
    text = re.sub(r'한 줄 소개:\s*', '', text)
    text = re.sub(r'상세 설명:\s*', '', text)
    
    # Clean up any incomplete words or artifacts
    text = re.sub(r'[가-힣]+[a-zA-Z0-9]+', '', text)  # Remove Korean+Latin mixed words
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = text.strip()
    
    return text


def _get_fallback_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    """Generate fallback description when AI response fails"""
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
    
    # Generate basic description
    description = f"이 모임은 {data.goal}을 목적으로 합니다. {data.period} 동안 진행되며, 관심있는 분들의 참여를 환영합니다. 함께 즐거운 시간을 보내며 좋은 인연을 만들어보세요."
    
    return summary, description


def _parse_alternative_format(response: str, data: GroupGenerationRequest) -> Tuple[str, str]:
    """Try alternative parsing when standard format fails"""
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    
    # Look for patterns in the response
    summary = ""
    description = ""
    
    for i, line in enumerate(lines):
        if not summary and len(line) < 50 and ("모임" in line or "스터디" in line or "동아리" in line):
            summary = line
        elif not description and len(line) > 30:
            # Likely a description line
            description = line
            # Try to get more description from following lines
            if i + 1 < len(lines):
                next_lines = lines[i+1:i+3]  # Get next 2 lines
                for next_line in next_lines:
                    if len(next_line) > 10 and not _is_text_corrupted(next_line):
                        description += " " + next_line
            break
    
    # Fallback if parsing still fails
    if not summary or not description or _is_text_corrupted(summary) or _is_text_corrupted(description):
        return _get_fallback_description(data)
    
    return summary, description

async def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = f"""[INFORMATION]
당신은 모임을 소개하는 AI 비서입니다.

다음 형식으로 정확히 출력하세요:

한 줄 소개: [모임의 핵심 목적을 50자 이내로 명사형 종결로 요약]
상세 설명: [300자 이내, 5문장 이내의 모임 소개]

요구사항:
- 한 줄 소개는 반드시 "모임", "동아리", "스터디" 등의 명사로 끝나야 합니다
- 상세 설명은 추천 대상과 분위기를 포함하여 작성하세요
- 문장을 완전히 마무리하여 작성하세요
- 한국어로만 작성하세요

입력 정보:
- 모임명: {data.name}
- 목적: {data.goal}  
- 카테고리: {data.category}
- 기간: {data.period}

출력 예시:
한 줄 소개: 맛집 탐방을 통한 친목 도모 모임
상세 설명: 이 모임은 판교의 다양한 맛집을 탐방하며 친목을 다지는 것을 목표로 합니다. 매주 1회 모여 서로의 취향을 공유하고, 다양한 장소를 경험하며 즐거운 시간을 보냅니다. 맛집을 좋아하고 새로운 사람들과 교류하고 싶은 분들께 추천합니다. 편안하고 즐거운 분위기에서 진행됩니다.

아래 형식으로 시작하세요:
한 줄 소개:"""
    try:
        ai_logger.info("[AI-v2] [요약 생성 시작]", extra={"meeting_name": data.name})

        # 로컬 모델로 교체 - with optimized parameters for Korean
        response = await call_vllm_api(prompt, max_tokens=512, temperature=0.3)
        raw = response.strip()

        # 결과 파싱 with enhanced error handling
        
        # Check for garbled/corrupted Korean text
        if _is_text_corrupted(response):
            ai_logger.warning("[AI-v2] [텍스트 손상 감지] 폴백 응답 사용", extra={"preview": response[:100]})
            return _get_fallback_description(data)
        
        parts = response.split("한 줄 소개:")
        if len(parts) < 2:
            ai_logger.warning("[AI-v2] [파싱 실패] '한 줄 소개' 구간 없음", extra={"preview": response[:80]})
            # Try alternative parsing
            return _parse_alternative_format(response, data)

        after_intro = parts[1]
        subparts = after_intro.split("상세 설명:")
        if len(subparts) < 2:
            ai_logger.warning("[AI-v2] [파싱 실패] '상세 설명' 구간 없음", extra={"preview": response[:80]})
            # Try alternative parsing
            return _parse_alternative_format(response, data)

        summary = subparts[0].strip()
        description = subparts[1].strip()
        
        # Validate extracted content
        if _is_text_corrupted(summary) or _is_text_corrupted(description):
            ai_logger.warning("[AI-v2] [추출된 텍스트 손상] 폴백 응답 사용")
            return _get_fallback_description(data)
        
        # Clean up any remaining artifacts
        summary = _clean_text_artifacts(summary)
        description = _clean_text_artifacts(description)

        ai_logger.info("[AI-v2] [모임 소개 생성 완료]",
                       extra={"summary_length": len(summary), "description_length": len(description)})
        return summary, description

    except Exception as e:
        ai_logger.exception("[AI-v2] [로컬모델 소개 생성 실패]")
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