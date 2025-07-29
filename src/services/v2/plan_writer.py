from src.schemas.v1.group_writer import GroupGenerationRequest
from src.core.ai_logger import get_ai_logger
from src.models.gemma_3_4b import call_vllm_api
import asyncio
import re
import httpx
from src.config import vLLM_URL, VLLM_TIMEOUT, VLLM_READ_TIMEOUT

ai_logger = get_ai_logger()


async def _call_vllm_for_plan(prompt: str) -> str:
    """
    Specialized VLLM call ONLY for plan generation
    Uses optimized parameters without affecting global VLLM behavior
    """
    VLLM_API_URL = f"{vLLM_URL.rstrip('/')}/v1/completions"
    
    # Specialized parameters ONLY for plan generation
    payload = {
        "prompt": prompt,
        "max_tokens": 500,  # Appropriate for plans
        "temperature": 0.5,  # Balanced for structured content
        "top_p": 0.9,
        "frequency_penalty": 0.6,  # Higher penalty for plans to avoid repetition
        "presence_penalty": 0.4,
        "stop": ["Step 9:", "Step 10:", "Step 11:", "```", "def ", "import ", "#", "\n\n\n\n"],  # Stop tokens specific to plans
        "repetition_penalty": 1.2,  # Higher for plans
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
        ai_logger.warning(f"[Plan VLLM] Specialized call failed: {e}")
        # Fallback to regular call if specialized fails
        return await call_vllm_api(prompt, max_tokens=500, temperature=0.5)


def _remove_duplicate_steps(text: str) -> str:
    """Remove duplicate steps and clean repetitive content"""
    if not text:
        return text
    
    # Extract all steps
    step_pattern = r'(Step\s*\d+:\s*[^\n]+(?:\n\s*-[^\n]*)*)'
    steps = re.findall(step_pattern, text, re.IGNORECASE | re.MULTILINE)
    
    if not steps:
        return text
    
    # Remove duplicate steps based on content similarity
    unique_steps = []
    seen_content = set()
    
    for step in steps:
        # Extract step content (without step number)
        content = re.sub(r'Step\s*\d+:\s*', '', step, flags=re.IGNORECASE)
        content_normalized = re.sub(r'[^\w가-힣]', '', content).lower()
        
        # Skip if we've seen similar content or if it's too short
        if content_normalized and len(content_normalized) > 10 and content_normalized not in seen_content:
            seen_content.add(content_normalized)
            unique_steps.append(step)
    
    # Limit to maximum 8 steps
    unique_steps = unique_steps[:8]
    
    # Renumber steps sequentially
    final_steps = []
    for i, step in enumerate(unique_steps, 1):
        # Replace step number with correct sequence
        renumbered_step = re.sub(
            r'Step\s*\d+:', 
            f'Step {i}:', 
            step, 
            flags=re.IGNORECASE
        )
        final_steps.append(renumbered_step)
    
    return '\n\n'.join(final_steps)


def _is_plan_corrupted(text: str) -> bool:
    """Check if plan text is corrupted - SPECIFIC to plan generation"""
    if not text or len(text.strip()) < 10:
        return True
    
    # Patterns specific to plan corruption
    corruption_patterns = [
        r'Step\s*\d+.*Step\s*\d+.*Step\s*\d+',  # Too many steps in one line
        r'(?:Step\s*\d+[^\n]*\n?){10,}',  # More than 10 steps (too many)
        r'Step\s*\d+:\s*$',  # Empty step
        r'Step.*코드.*함수',  # Contains code/function references
        r'def\s+\w+|import\s+\w+|```|#\s*Step',  # Code artifacts
        r'Step\s*\d+.*(?:Step\s*\1[^0-9])',  # Duplicate step numbers
    ]
    
    for pattern in corruption_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Check if steps are properly formatted
    step_count = len(re.findall(r'Step\s*\d+:', text, re.IGNORECASE))
    if step_count == 0 or step_count > 8:  # Should have 1-8 steps
        return True
    
    # Check for excessive repetition in plans
    lines = text.split('\n')
    line_count = {}
    for line in lines:
        line = line.strip()
        if len(line) > 10:
            normalized = re.sub(r'[^\w가-힣]', '', line).lower()
            line_count[normalized] = line_count.get(normalized, 0) + 1
    
    # If any line appears more than twice, likely repetitive
    if any(count > 2 for count in line_count.values()):
        return True
    
    return False


def _clean_plan_artifacts(text: str) -> str:
    """Clean plan-specific artifacts"""
    if not text:
        return text
    
    # Remove any code-like content (specific to plans)
    text = re.sub(r'```[^`]*```', '', text, flags=re.MULTILINE)
    text = re.sub(r'`[^`]*`', '', text)
    
    # Remove function/code references
    text = re.sub(r'def\s+\w+.*?:', '', text)
    text = re.sub(r'import\s+\w+.*', '', text)
    text = re.sub(r'#\s*[^\n]*', '', text)  # Remove comment lines
    
    # Clean up step formatting
    text = re.sub(r'Step\s*(\d+)\s*:', r'Step \1:', text, flags=re.IGNORECASE)
    
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 consecutive newlines
    text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces
    
    # Remove incomplete sentences at the end (specific to plans)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            # If line doesn't end properly and looks incomplete, skip it
            if len(line) > 5 and not re.search(r'[다요니까습니다음겠앙함면동\.]$', line):
                # Check if it's a bullet point or step header
                if not (line.startswith('-') or re.match(r'Step\s*\d+:', line, re.IGNORECASE)):
                    continue  # Skip incomplete content lines
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def _generate_fallback_plan(data: GroupGenerationRequest) -> str:
    """Generate a simple fallback plan"""
    category_plans = {
        "스터디": [
            "모집 및 계획 수립",
            "학습 자료 준비 및 일정 조율", 
            "정기 모임 진행 및 학습",
            "중간 점검 및 피드백",
            "목표 달성 및 평가"
        ],
        "취미": [
            "참여자 모집 및 소개",
            "활동 계획 및 준비",
            "정기 활동 진행",
            "경험 공유 및 발전"
        ],
        "친목": [
            "멤버 모집 및 만남",
            "친목 활동 계획",
            "정기 모임 진행",
            "관계 발전 및 유지"
        ],
        "운동": [
            "참여자 모집 및 레벨 확인",
            "운동 계획 및 장소 섭외",
            "정기 운동 진행",
            "성과 확인 및 목표 조정"
        ]
    }
    
    # Find matching category
    category_key = next((key for key in category_plans.keys() if key in data.category), "친목")
    base_steps = category_plans[category_key]
    
    # Generate plan text
    plan_lines = []
    for i, step in enumerate(base_steps, 1):
        plan_lines.append(f"Step {i}: {step}")
        plan_lines.append(f"        - {data.goal}과 관련된 구체적인 활동을 진행합니다.")
        plan_lines.append(f"        - 참여자들과 소통하며 목표를 달성해 나갑니다.")
        plan_lines.append("")
    
    return '\n'.join(plan_lines).strip()


def clean_output_to_steps(text: str) -> str:
    """Enhanced step cleaning with repetition prevention"""
    if not text:
        return text
    
    # Find steps section
    match = re.search(r"(Step\s*1[\s\S]*)", text, re.IGNORECASE)
    if not match:
        return text.strip()

    steps_text = match.group(1).strip()
    
    # Remove duplicates
    steps_text = _remove_duplicate_steps(steps_text)
    
    # Clean artifacts
    steps_text = _clean_plan_artifacts(steps_text)
    
    # Clean up indentation for step headers only
    cleaned_lines = []
    for line in steps_text.splitlines():
        if re.match(r"\s*Step\s*\d+:", line, re.IGNORECASE):
            cleaned_lines.append(line.lstrip())  # Remove indentation from step headers
        else:
            cleaned_lines.append(line)  # Keep original formatting for content
    
    result = "\n".join(cleaned_lines)
    
    return result


async def generate_plan(data: GroupGenerationRequest) -> str:
    """Enhanced plan generation with targeted repetition prevention"""
    
    # Improved prompt to prevent repetition and code generation
    prompt = f"""모임 계획을 단계별로 작성하세요.

요구사항:
1. 4-6단계로 구성하세요
2. 각 단계는 실제 실행 가능한 활동이어야 합니다
3. 코드나 프로그래밍 내용은 포함하지 마세요
4. 같은 내용을 반복하지 마세요
5. 각 단계마다 구체적인 설명을 포함하세요

모임 정보:
- 이름: {data.name}
- 목적: {data.goal}
- 분야: {data.category}
- 기간: {data.period}

형식:
Step 1: [단계 제목]
        - [구체적인 활동 설명]
        - [추가 세부사항]

Step 1:"""

    try:
        ai_logger.info("[AI-v2] [커리큘럼 생성 시작]", extra={"meeting_name": data.name})
        
        # Use specialized VLLM call for plans
        response = await _call_vllm_for_plan(prompt)

        if not response or _is_plan_corrupted(response):
            ai_logger.warning("[AI-v2] [계획 손상 감지] 폴백 사용")
            return _generate_fallback_plan(data)

        # Clean and process
        plan_text = clean_output_to_steps(response)
        
        # Final validation
        if _is_plan_corrupted(plan_text) or len(plan_text.strip()) < 20:
            ai_logger.warning("[AI-v2] [최종 검증 실패] 폴백 사용")
            return _generate_fallback_plan(data)

        step_count = len(re.findall(r'Step\s*\d+:', plan_text, re.IGNORECASE))
        
        ai_logger.info("[AI-v2] [커리큘럼 생성 완료]",
                      extra={
                          "steps": step_count, 
                          "text_length": len(plan_text)
                      })
        
        return plan_text

    except Exception as e:
        ai_logger.exception("[AI-v2] [계획 생성 실패]")
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
