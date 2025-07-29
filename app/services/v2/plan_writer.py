from app.schemas.groups.group_writer import GroupGenerationRequest
from app.core.ai_logger import get_ai_logger
from app.models.gemma_3_4b import call_vllm_api  # 로컬 모델 호출로 교체
from app.prompts.prompt_loader import load_prompt_template
import asyncio
import re

ai_logger = get_ai_logger()

def _remove_pii_from_plan(text: str) -> str:
    """Remove PII and sensitive information from plan text"""
    if not text:
        return text
    
    # PII patterns to remove
    pii_patterns = [
        r'\b\d{2,3}-\d{3,4}-\d{4}\b',  # Phone numbers
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # Email addresses
        r'\b\d{3}-\d{2}-\d{5}\b',  # Registration numbers
        r'\bhttps?://[^\s]+',  # URLs
        r'\b\d{5}-\d{5}\b',  # Postal codes
        r'\b\d{4}\.\d{2}\.\d{2}\b',  # Date patterns
        r'\b[0-9,]+원\b',  # Money amounts
        r'\b담당자[:\s]*[가-힣]{2,4}\b',  # Contact person names
        r'\b문의[:\s]*\([0-9-]+\)',  # Contact inquiry
    ]
    
    cleaned_text = text
    for pattern in pii_patterns:
        cleaned_text = re.sub(pattern, '[정보삭제]', cleaned_text, flags=re.IGNORECASE)
    
    return cleaned_text

def _remove_irrelevant_content_from_plan(text: str, topic_context: str = "") -> str:
    """Remove irrelevant content from plan text"""
    if not text:
        return text
    
    # Irrelevant keywords that shouldn't be in plans
    irrelevant_keywords = [
        '한국건설기술인협회', '건설워크넷', '프로젝트비', '보고서 형태',
        '전문가 자문', '팀 연구', '성과 지표', '기대 효과', '홈페이지',
        '이메일', '담당자', '참고사항', '본 프로젝트는', '외부 전문가'
    ]
    
    # If the topic context doesn't include construction but the text does, filter it
    if topic_context and "건설" not in topic_context.lower():
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            line_clean = True
            for keyword in irrelevant_keywords:
                if keyword in line:
                    line_clean = False
                    break
            
            if line_clean:
                clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    return text

def clean_output_to_steps(text: str) -> str:
    """Clean and extract step-based content from response"""
    if not text:
        return ""
    
    # Remove PII first
    text = _remove_pii_from_plan(text)
    
    # Find step-based content
    match = re.search(r"(Step\s*1[\s\S]*)", text, re.IGNORECASE)
    if not match:
        # If no Step 1 found, look for any step-like content
        step_pattern = r'((?:Step\s*\d+|단계\s*\d+)[\s\S]*?)(?=(?:Step\s*\d+|단계\s*\d+)|$)'
        steps = re.findall(step_pattern, text, re.IGNORECASE)
        if steps:
            text = '\n\n'.join(steps)
        else:
            return text.strip()
    else:
        text = match.group(1).strip()

    # Clean up formatting
    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            cleaned_lines.append('')
            continue
            
        # Remove indentation from step headers
        if re.match(r"\s*Step\s*\d+:", line, re.IGNORECASE):
            cleaned_lines.append(line.lstrip())
        else:
            cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines)

def _generate_fallback_plan(data: GroupGenerationRequest) -> str:
    """Generate a basic fallback plan when AI generation fails"""
    
    plan_parts = []
    
    plan_parts.append(f"Step 1: 모임 시작 및 목표 설정")
    plan_parts.append(f" - {data.goal}에 대한 구체적인 계획을 세웁니다.")
    plan_parts.append(f" - 참여자들의 기대사항과 목표를 공유합니다.")
    plan_parts.append(f" - 모임 진행 방식과 규칙을 정합니다.")
    
    if "스터디" in data.category or "학습" in data.category or "개발" in data.category:
        plan_parts.append(f"\nStep 2: 학습 계획 수립")
        plan_parts.append(f" - 학습할 내용과 범위를 정합니다.")
        plan_parts.append(f" - 개인별 학습 진도와 목표를 설정합니다.")
        plan_parts.append(f" - 정기적인 진도 점검 방법을 결정합니다.")
        
        plan_parts.append(f"\nStep 3: 실습 및 토론")
        plan_parts.append(f" - 학습한 내용을 바탕으로 실습을 진행합니다.")
        plan_parts.append(f" - 참여자들과 학습 내용에 대해 토론합니다.")
        plan_parts.append(f" - 어려운 부분은 함께 해결해 나갑니다.")
        
        plan_parts.append(f"\nStep 4: 프로젝트 또는 결과물 제작")
        plan_parts.append(f" - 학습한 내용을 활용한 프로젝트를 진행합니다.")
        plan_parts.append(f" - 개인 또는 팀별 결과물을 만들어봅니다.")
        plan_parts.append(f" - 서로의 결과물을 공유하고 피드백합니다.")
        
    elif "운동" in data.category or "건강" in data.category:
        plan_parts.append(f"\nStep 2: 운동 계획 수립")
        plan_parts.append(f" - 개인별 체력 수준을 확인합니다.")
        plan_parts.append(f" - 안전한 운동 방법을 익힙니다.")
        plan_parts.append(f" - 정기적인 운동 일정을 정합니다.")
        
        plan_parts.append(f"\nStep 3: 함께 운동하기")
        plan_parts.append(f" - 계획된 운동을 함께 실행합니다.")
        plan_parts.append(f" - 서로 동기부여하며 꾸준히 참여합니다.")
        plan_parts.append(f" - 운동 효과를 함께 점검합니다.")
        
    else:
        plan_parts.append(f"\nStep 2: 활동 계획 및 준비")
        plan_parts.append(f" - 모임에서 진행할 활동들을 계획합니다.")
        plan_parts.append(f" - 필요한 준비물이나 자료를 확인합니다.")
        plan_parts.append(f" - 참여자들의 역할을 분담합니다.")
        
        plan_parts.append(f"\nStep 3: 활동 진행 및 소통")
        plan_parts.append(f" - 계획된 활동을 함께 진행합니다.")
        plan_parts.append(f" - 참여자들과 적극적으로 소통합니다.")
        plan_parts.append(f" - 즐거운 시간을 보내며 친목을 도모합니다.")
    
    plan_parts.append(f"\nStep 5: 마무리 및 평가")
    plan_parts.append(f" - 모임 활동에 대해 함께 평가합니다.")
    plan_parts.append(f" - 좋았던 점과 개선할 점을 나눕니다.")
    plan_parts.append(f" - 앞으로의 계획에 대해 논의합니다.")
    
    return '\n'.join(plan_parts)

async def generate_plan(data: GroupGenerationRequest) -> str:
    prompt = load_prompt_template("plan_writer_v2",
                                  name=data.name,
                                  goal=data.goal,
                                  category=data.category,
                                  period=data.period)
    try:
        ai_logger.info("[AI-V2] [커리큘럼 생성 시작]", extra={"meeting_name": data.name})
        
        # Call local model with better parameters for plan generation
        response = await call_vllm_api(prompt, max_tokens=700, temperature=0.4)
        
        if not response or not response.strip():
            ai_logger.warning("[AI-V2] [빈 응답] 폴백 계획 사용")
            return _generate_fallback_plan(data)

        # Clean and process the response
        plan_text = response.strip() if isinstance(response, str) else str(response)
        
        # Remove irrelevant content based on topic context
        topic_context = f"{data.name} {data.goal} {data.category}"
        plan_text = _remove_irrelevant_content_from_plan(plan_text, topic_context)
        
        # Extract and clean step-based content
        cleaned_plan = clean_output_to_steps(plan_text)
        
        if not cleaned_plan or len(cleaned_plan.strip()) < 50:
            ai_logger.warning("[AI-V2] [계획이 너무 짧음] 폴백 계획 사용")
            return _generate_fallback_plan(data)
        
        step_count = cleaned_plan.count("Step ")
        ai_logger.info("[AI-V2] [커리큘럼 생성 완료]",
                       extra={"steps": step_count, "text_length": len(cleaned_plan)})
        
        return cleaned_plan

    except Exception as e:
        ai_logger.exception("[AI-V2] [로컬모델 단계별 계획 생성 실패]")
        return _generate_fallback_plan(data)


if __name__ == "__main__":
    data = GroupGenerationRequest(
        name="RAG 스터디 모임",
        goal="RAG 이론 공부하기",
        category="개발",
        period="1개월 이하",
        isPlanCreated=True
    )

    async def run_test():
        plan = await generate_plan(data)
        print("\n생성된 커리큘럼:\n")
        print(plan)

    asyncio.run(run_test())
