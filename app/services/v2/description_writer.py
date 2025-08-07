from typing import Tuple
from app.schemas.groups.group_writer import GroupGenerationRequest
# from app.core.cloud_logging import logger
from app.core.ai_logger import get_ai_logger
from app.models.text_generation_model import call_vllm_api   #로컬 모델 호출로 교체
from app.prompts.prompt_loader import load_prompt_template
import re

ai_logger = get_ai_logger()


def _clean_text_artifacts(text: str) -> str:
    """Clean up any text artifacts or formatting issues"""
    if not text:
        return text
    
    # Remove any remaining format indicators
    text = re.sub(r'한 줄 소개:\s*', '', text)
    text = re.sub(r'상세 설명:\s*', '', text)
    text = re.sub(r'요약:\s*', '', text)
    text = re.sub(r'소개:\s*', '', text)
    
    # Remove leading/trailing quotes or brackets
    text = re.sub(r'^["\'\[\]]+|["\'\[\]]+$', '', text)
    
    # Clean up any incomplete words or artifacts
    text = re.sub(r'[가-힣]+[a-zA-Z0-9]+', '', text)  # Remove Korean+Latin mixed words
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = text.strip()
    
    return text


def _remove_pii_and_irrelevant_content(text: str) -> str:
    """Remove PII and irrelevant content from text"""
    if not text:
        return text
    
    # PII patterns to remove
    pii_patterns = [
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
    
    # Replace PII with placeholder
    cleaned_text = text
    for pattern in pii_patterns:
        cleaned_text = re.sub(pattern, '[정보삭제]', cleaned_text, flags=re.IGNORECASE)
    
    # Remove sentences containing irrelevant content
    irrelevant_keywords = [
        '한국건설기술인협회', '건설워크넷', '프로젝트비', '보고서 형태',
        '전문가 자문', '팀 연구', '성과 지표', '기대 효과', '홈페이지',
        '이메일', '담당자', '참고사항', '본 프로젝트는', '외부 전문가'
    ]
    
    sentences = re.split(r'[.!?]\s*', cleaned_text)
    relevant_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and not any(keyword in sentence for keyword in irrelevant_keywords):
            relevant_sentences.append(sentence)
    
    if relevant_sentences:
        cleaned_text = '. '.join(relevant_sentences)
        if not cleaned_text.endswith('.'):
            cleaned_text += '.'
    
    return cleaned_text


def _get_fallback_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    """Generate fallback description when AI response fails"""
    # Create a meaningful summary based on input
    summary = f"{data.category} 분야의 {data.name}"
    if "모임" not in summary and "스터디" not in summary and "동아리" not in summary:
        summary += " 모임"
    
    # Create a meaningful description
    description = f"이 모임은 {data.goal}을 목적으로 {data.period} 동안 진행됩니다."
    
    # Add category-specific content
    if "스터디" in data.category or "학습" in data.category:
        description += " 함께 학습하며 목표를 달성하고 성장할 수 있는 기회를 제공합니다."
    elif "운동" in data.category or "건강" in data.category:
        description += " 건강한 활동을 통해 체력 향상과 친목을 도모할 수 있습니다."
    elif "취미" in data.category:
        description += " 공통 관심사를 바탕으로 즐거운 시간을 보내며 새로운 경험을 쌓을 수 있습니다."
    elif "친목" in data.category or "사교" in data.category:
        description += " 새로운 사람들과 만나 소통하며 즐거운 시간을 보낼 수 있습니다."
    else:
        description += " 관심있는 분들과 함께 유익한 시간을 보낼 수 있는 모임입니다."
    
    description += " 적극적인 참여를 환영합니다."
    
    return summary, description


def _parse_alternative_format(response: str, data: GroupGenerationRequest) -> Tuple[str, str]:
    """Try alternative parsing when standard format fails"""
    
    # Clean the response first
    response = _remove_pii_and_irrelevant_content(response)
    
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    
    # Look for patterns in the response
    summary = ""
    description = ""
    
    for i, line in enumerate(lines):
        if not summary and 20 < len(line) < 80 and any(word in line for word in ["모임", "스터디", "동아리", "그룹"]):
            candidate = _clean_text_artifacts(line)
            summary = candidate
        elif not description and len(line) > 40:
            # Likely a description line
            candidate = _clean_text_artifacts(line)
            description = candidate
            # Try to get more description from following lines
            for j in range(i+1, min(i+3, len(lines))):
                next_line = lines[j]
                if (len(next_line) > 15 and 
                    not next_line.startswith("Step") and 
                    ":" not in next_line[:10]):
                    description += " " + _clean_text_artifacts(next_line)
                else:
                    break
            break
    
    # Fallback if parsing still fails
    if not summary or not description or len(summary) < 10 or len(description) < 20:
        return _get_fallback_description(data)
    
    return summary, description


def _extract_meaningful_content(response: str, data: GroupGenerationRequest) -> Tuple[str, str]:
    """Extract meaningful content when standard parsing completely fails"""
    
    # Remove unwanted patterns and PII first
    clean_response = _remove_pii_and_irrelevant_content(response)
    
    # Remove common unwanted patterns
    clean_response = re.sub(r'Step \d+:', '', clean_response)
    clean_response = re.sub(r'-\s*', '', clean_response)
    clean_response = re.sub(r'\n+', ' ', clean_response)
    
    # Split into sentences and clean them
    sentences = re.split(r'[.!?]\s*', clean_response)
    clean_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if (sentence and len(sentence) > 10 and
            not any(word in sentence.lower() for word in ['step', 'phase', '단계'])):
            clean_sentences.append(sentence)
    
    if not clean_sentences:
        return _get_fallback_description(data)
    
    # Find suitable summary (shorter sentence with meeting-related terms)
    summary = ""
    for sentence in clean_sentences:
        if (20 < len(sentence) < 80 and 
            any(word in sentence for word in ["모임", "스터디", "동아리", "그룹", "활동"])):
            summary = sentence
            break
    
    if not summary and clean_sentences:
        # Use first suitable sentence as summary
        for sentence in clean_sentences:
            if 15 < len(sentence) < 100:
                summary = sentence
                break
    
    # Find suitable description (combine several sentences)
    description_sentences = []
    for sentence in clean_sentences:
        if sentence != summary and len(sentence) > 15:
            description_sentences.append(sentence)
            if len('. '.join(description_sentences)) > 80:
                break
    
    description = '. '.join(description_sentences)
    if description and not description.endswith('.'):
        description += '.'
    
    # Final validation
    if not summary or not description or len(summary) < 10 or len(description) < 20:
        return _get_fallback_description(data)
    
    return summary, description


async def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = load_prompt_template("description_writer", "v2",
                                  data=data)
    
    try:
        ai_logger.info("[AI-V2] [요약 생성 시작]", extra={"meeting_name": data.name})

        # Use local model with optimized parameters for Korean
        response = await call_vllm_api(prompt, max_tokens=512, temperature=0.3)
        
        if not response:
            ai_logger.warning("[AI-V2] [빈 응답] 폴백 콘텐츠 사용")
            return _get_fallback_description(data)
        
        # Check for corruption early
        response = response.strip()
        
        # Primary parsing method
        summary = ""
        description = ""
        
        parts = response.split("한 줄 소개:")
        if len(parts) >= 2:
            after_intro = parts[1]
            subparts = after_intro.split("상세 설명:")
            if len(subparts) >= 2:
                summary_candidate = _clean_text_artifacts(subparts[0])
                description_candidate = _clean_text_artifacts(subparts[1])
                
                # Validate and clean candidates
                if (len(summary_candidate) >= 10 and len(description_candidate) >= 20):
                    
                    summary = _remove_pii_and_irrelevant_content(summary_candidate)
                    description = _remove_pii_and_irrelevant_content(description_candidate)

        # If primary parsing failed, try alternative methods
        if not summary or not description or len(summary) < 10 or len(description) < 20:
            ai_logger.warning("[AI-V2] [표준 파싱 실패] 대안 파싱 시도", extra={"preview": response[:100]})
            try:
                summary, description = _parse_alternative_format(response, data)
            except Exception:
                ai_logger.warning("[AI-V2] [대안 파싱 실패] 내용 추출 시도")
                summary, description = _extract_meaningful_content(response, data)

        # Final validation and cleanup
        if not summary or not description or len(summary) < 10 or len(description) < 20:
            ai_logger.warning("[AI-V2] [모든 파싱 실패] 폴백 콘텐츠 사용")
            summary, description = _get_fallback_description(data)

        ai_logger.info("[AI-V2] [모임 소개 생성 완료]",
                       extra={"summary_length": len(summary), "description_length": len(description)})
        return summary, description

    except Exception as e:
        ai_logger.exception("[AI-V2] [로컬모델 소개 생성 실패]")
        return _get_fallback_description(data)


if __name__ == "__main__":
    import asyncio
    from app.schemas.groups.group_writer import GroupGenerationRequest

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
