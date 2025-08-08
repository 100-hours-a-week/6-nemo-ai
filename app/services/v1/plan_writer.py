from app.schemas.groups.group_writer import GroupGenerationRequest
from app.core.ai_logger import get_ai_logger
from app.core.vertex_client import smart_generate
from app.prompts.prompt_loader import load_prompt_template
import asyncio
import re

ai_logger = get_ai_logger()


def _clean_plan_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    
    text = text.strip()
    
    lines = text.split('\n')
    clean_lines = []
    
    skip_patterns = [
        r'^모임명:',
        r'^목적:',
        r'^카테고리:',
        r'^기간:',
        r'^한 줄 소개:',
        r'^상세 설명:',
        r'^요약:',
        r'^소개:',
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip metadata lines
        if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
            continue
            
        # Only keep lines that are part of the actual plan
        if (line.startswith('Step ') or 
            line.startswith('- ') or 
            line.startswith('단계 ') or
            (len(line) > 20 and any(word in line for word in ['진행', '학습', '실습', '활동', '모임']))):
            clean_lines.append(line)
    
    if not clean_lines:
        return ""
    
    return '\n'.join(clean_lines)


def _extract_plan_from_mixed_content(text: str) -> str:
    if not text:
        return ""
    
    step_pattern = r'(Step \d+:.*?)(?=Step \d+:|$)'
    steps = re.findall(step_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if steps:
        plan_content = '\n\n'.join(step.strip() for step in steps)
        return _clean_plan_text(plan_content)
    
    lines = text.split('\n')
    plan_lines = []
    
    in_plan_section = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if (line.startswith('Step ') or
            line.startswith('단계 ') or
            '진행 방법' in line or
            '계획' in line and ':' in line):
            in_plan_section = True
        
        if in_plan_section:
            if not any(re.match(pattern, line, re.IGNORECASE) for pattern in [
                r'^모임명:', r'^목적:', r'^카테고리:', r'^기간:']):
                plan_lines.append(line)
    
    if plan_lines:
        return '\n'.join(plan_lines)
    
    return ""


def _generate_fallback_plan(data: GroupGenerationRequest) -> str:
    plan_parts = []
    
    plan_parts.append(f"Step 1: 모임 시작 및 목표 설정")
    plan_parts.append(f" - {data.goal}에 대한 구체적인 계획을 세웁니다.")
    plan_parts.append(f" - 참여자들의 기대사항과 목표를 공유합니다.")
    plan_parts.append(f" - 모임 진행 방식과 규칙을 정합니다.")
    
    if "스터디" in data.category or "학습" in data.category:
        plan_parts.append(f"\nStep 2: 학습 계획 수립")
        plan_parts.append(f" - 학습할 내용과 범위를 정합니다.")
        plan_parts.append(f" - 개인별 학습 진도와 목표를 설정합니다.")
        plan_parts.append(f" - 정기적인 진도 점검 방법을 결정합니다.")
        
        plan_parts.append(f"\nStep 3: 실습 및 토론")
        plan_parts.append(f" - 학습한 내용을 바탕으로 실습을 진행합니다.")
        plan_parts.append(f" - 참여자들과 학습 내용에 대해 토론합니다.")
        plan_parts.append(f" - 어려운 부분은 함께 해결해 나갑니다.")
        
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
    
    plan_parts.append(f"\nStep 4: 마무리 및 평가")
    plan_parts.append(f" - 모임 활동에 대해 함께 평가합니다.")
    plan_parts.append(f" - 좋았던 점과 개선할 점을 나눕니다.")
    plan_parts.append(f" - 앞으로의 계획에 대해 논의합니다.")
    
    return '\n'.join(plan_parts)


async def generate_plan(data: GroupGenerationRequest) -> str:
    prompt = load_prompt_template("plan_writer", "v1",
                                  name=data.name,
                                  goal=data.goal,
                                  category=data.category,
                                  period=data.period)
    try:
        ai_logger.info("[AI-V1] [커리큘럼 생성 시작]", extra={"meeting_name": data.name})
        response = await smart_generate(prompt)
        
        if not response or not response.strip():
            ai_logger.warning("[AI-V1] [빈 응답] 폴백 계획 사용")
            return _generate_fallback_plan(data)
        
        result = response.strip()
        
        cleaned_plan = _extract_plan_from_mixed_content(result)
        
        if not cleaned_plan:
            cleaned_plan = _clean_plan_text(result)
        
        if not cleaned_plan:
            ai_logger.warning("[AI-V1] [계획 추출 실패] 폴백 계획 사용")
            return _generate_fallback_plan(data)
        
        step_count = cleaned_plan.count("Step ")
        ai_logger.info("[AI-V1] [커리큘럼 생성 완료]", extra={
            "steps": step_count, 
            "text_length": len(cleaned_plan),
            "has_metadata": len(cleaned_plan) < len(result)
        })
        
        return cleaned_plan

    except Exception as e:
        ai_logger.exception("[AI-V1] [Vertex Gemini 단계별 계획 생성 실패]")
        return _generate_fallback_plan(data)


if __name__ == "__main__":
    data = GroupGenerationRequest(
        name="토익 스터디 모임",
        goal="함께 공부해서 다음 달 토익 시험 목표 점수 달성하기",
        category="학습/자기계발",
        period="2주",
        isPlanCreated=False
    )

    async def run_test():
        plan = await generate_plan(data)
        print("\n생성된 커리큘럼:\n")
        print(plan)

    asyncio.run(run_test())
