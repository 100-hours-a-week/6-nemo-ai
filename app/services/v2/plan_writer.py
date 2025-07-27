from app.schemas.groups.group_writer import GroupGenerationRequest
from app.core.ai_logger import get_ai_logger
from app.models.gemma_3_4b import call_vllm_api  # 로컬 모델 호출로 교체
from app.prompts.prompt_loader import load_prompt_template
import asyncio
import re

ai_logger = get_ai_logger()

def clean_output_to_steps(text:str) -> str:
    match = re.search(r"(Step\s*1[\s\S]*)", text, re.IGNORECASE)
    if not match:
        return text.strip()

    steps_text = match.group(1).strip()

    # 줄별로 순회하며 Step N: 앞의 들여쓰기만 제거
    cleaned_lines = []
    for line in steps_text.splitlines():
        if re.match(r"\s*Step\s*\d+:", line, re.IGNORECASE):
            cleaned_lines.append(line.lstrip())   #들여쓰기 제거
        else:
            cleaned_lines.append(line) # 유지
    return "\n".join(cleaned_lines)

async def generate_plan(data: GroupGenerationRequest) -> str:
    prompt = load_prompt_template("plan_writer_v2",
                                  name=data.name,
                                  goal=data.goal,
                                  category=data.category,
                                  period=data.period)
    try:
        ai_logger.info("[AI-v2] [커리큘럼 생성 시작]", extra={"meeting_name": data.name})
        # 로컬 모델 호출로 교체
        response = await call_vllm_api(prompt, max_tokens=700)

        # 문자열로 추정되는 경우 바로 처리
        plan_text = response.strip() if isinstance(response, str) else str(response)
        step_count = plan_text.count("Step ")

        ai_logger.info("[AI-v2] [커리큘럼 생성 완료]",
                       extra={"steps": step_count, "text_length": len(plan_text)})
        return clean_output_to_steps(plan_text)

    except Exception:
        ai_logger.exception("[AI-v2] [로컬모델 단계별 계획 생성 실패]")
        return ""


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