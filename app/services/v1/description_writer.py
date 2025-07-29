from typing import Tuple
from app.schemas.groups.group_writer import GroupGenerationRequest
# from app.core.cloud_logging import logger
from app.core.ai_logger import get_ai_logger
from app.core.vertex_client import smart_generate
from app.prompts.prompt_loader import load_prompt_template
import asyncio
import re

ai_logger = get_ai_logger()

def _clean_and_validate_text(text: str, field_name: str, min_length: int = 5) -> str:
    """Clean and validate extracted text"""
    if not text or not isinstance(text, str):
        return ""
    
    # Clean up the text
    text = text.strip()
    
    # Remove any remaining format indicators
    text = re.sub(r'한 줄 소개:\s*', '', text)
    text = re.sub(r'상세 설명:\s*', '', text)
    text = re.sub(r'요약:\s*', '', text)
    text = re.sub(r'소개:\s*', '', text)
    
    # Remove leading/trailing quotes or brackets
    text = re.sub(r'^["\'\[\]]+|["\'\[\]]+$', '', text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Validate minimum length
    if len(text) < min_length:
        ai_logger.warning(f"[AI-V1] [{field_name}] 텍스트가 너무 짧음: {len(text)}자")
        return ""
    
    return text

def _get_fallback_content(data: GroupGenerationRequest) -> Tuple[str, str]:
    """Generate fallback content when AI parsing fails"""
    # Create a meaningful summary based on input
    summary = f"{data.category} 분야의 {data.name}"
    if "모임" not in summary and "스터디" not in summary:
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
    else:
        description += " 관심있는 분들과 함께 유익한 시간을 보낼 수 있는 모임입니다."
    
    description += " 적극적인 참여를 환영합니다."
    
    return summary, description

def _try_alternative_parsing(response: str, data: GroupGenerationRequest) -> Tuple[str, str]:
    """Try alternative parsing methods when standard parsing fails"""
    
    # Method 1: Look for line-based content
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    
    potential_summary = ""
    potential_description = ""
    
    for i, line in enumerate(lines):
        # Look for a short summary-like line
        if not potential_summary and 20 < len(line) < 80 and ("모임" in line or "스터디" in line or "동아리" in line):
            potential_summary = line
        # Look for longer description content
        elif len(line) > 50 and not potential_description:
            potential_description = line
            # Try to append next few lines if they seem to be part of description
            for j in range(i+1, min(i+4, len(lines))):
                if len(lines[j]) > 20 and not lines[j].startswith("Step") and ":" not in lines[j][:10]:
                    potential_description += " " + lines[j]
                else:
                    break
            break
    
    # Clean and validate
    if potential_summary:
        potential_summary = _clean_and_validate_text(potential_summary, "대안_요약", 10)
    if potential_description:
        potential_description = _clean_and_validate_text(potential_description, "대안_설명", 20)
    
    # Method 2: If still empty, try to extract any meaningful Korean text
    if not potential_summary or not potential_description:
        # Remove common unwanted patterns and extract Korean sentences
        clean_text = re.sub(r'Step \d+:', '', response)
        clean_text = re.sub(r'-\s*', '', clean_text)
        
        # Split into sentences and find suitable ones
        sentences = re.split(r'[.!?]\s*', clean_text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        if not potential_summary and sentences:
            # Look for a good summary sentence
            for sentence in sentences:
                if 20 < len(sentence) < 80 and any(word in sentence for word in ["모임", "스터디", "동아리", "그룹"]):
                    potential_summary = sentence
                    break
        
        if not potential_description and sentences:
            # Combine several sentences for description
            description_sentences = []
            for sentence in sentences:
                if len(sentence) > 20 and sentence != potential_summary:
                    description_sentences.append(sentence)
                    if len(" ".join(description_sentences)) > 100:
                        break
            
            if description_sentences:
                potential_description = ". ".join(description_sentences)
                if not potential_description.endswith('.'):
                    potential_description += '.'
    
    # Final validation and fallback
    if not potential_summary or not potential_description:
        ai_logger.warning("[AI-V1] [대안 파싱도 실패] 폴백 콘텐츠 사용")
        return _get_fallback_content(data)
    
    return potential_summary, potential_description

async def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = load_prompt_template("description_writer_v1",
                                  name=data.name,
                                  goal=data.goal,
                                  category=data.category,
                                  period=data.period)
    try:
        ai_logger.info("[AI-V1] [요약 생성 시작]", extra={"meeting_name": data.name})
        response = await smart_generate(prompt)

        # Enhanced parsing with multiple fallback strategies
        summary = ""
        description = ""
        
        # Primary parsing method
        parts = response.split("한 줄 소개:")
        if len(parts) >= 2:
            after_intro = parts[1]
            subparts = after_intro.split("상세 설명:")
            if len(subparts) >= 2:
                summary = _clean_and_validate_text(subparts[0], "요약", 10)
                description = _clean_and_validate_text(subparts[1], "설명", 20)

        # If primary parsing failed, try alternative methods
        if not summary or not description:
            ai_logger.warning("[AI-V1] [표준 파싱 실패] 대안 파싱 시도", extra={"preview": response[:100]})
            summary, description = _try_alternative_parsing(response, data)

        # Final validation
        if not summary or not description:
            ai_logger.warning("[AI-V1] [모든 파싱 실패] 폴백 콘텐츠 사용")
            summary, description = _get_fallback_content(data)

        ai_logger.info("[AI-V1] [모임 소개 생성 완료]",
                       extra={"summary_length": len(summary), "description_length": len(description)})
        return summary, description

    except Exception as e:
        ai_logger.exception("[AI-V1] [Vertex Gemini 소개 생성 실패]")
        return _get_fallback_content(data)

if __name__ == "__main__":
    import asyncio
    from app.schemas.groups.group_writer import GroupGenerationRequest

    data = GroupGenerationRequest(
        name="주말 러닝 크루",
        goal="매주 함께 뛰며 체력과 건강을 관리하기",
        category="운동/건강",
        period="3개월",
        isPlanCreated=False
    )

    async def run_test():
        summary, description = await generate_description(data)
        print("\n한 줄 소개:\n", summary)
        print("\n상세 설명:\n", description)

    asyncio.run(run_test())
