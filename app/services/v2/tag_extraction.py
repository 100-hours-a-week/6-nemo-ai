import json
import re
# from app.core.cloud_logging import logger
from app.models.gemma_3_4b import call_vllm_api   # 로컬 모델로 교체
from app.core.ai_logger import get_ai_logger
from app.prompts.prompt_loader import load_prompt_template

ai_logger = get_ai_logger()

async def extract_tags(text: str) -> list[str]:
    prompt = load_prompt_template("tag_extraction_v2", text=text)

    try:
        ai_logger.info("[AI-v2] [태그 추출 시작]", extra={"text_length": len(text)})
        response = await call_vllm_api(prompt, max_tokens=128)
        raw = response.strip()

        try:
            tags = json.loads(raw)
        except json.JSONDecodeError:
            ai_logger.info("[AI-v2] [JSON 파싱 실패] 태그 정규식으로 대체 처리", extra={"raw_preview": raw[:80]})
            tags = re.findall(r'"(.*?)"', raw)

        ai_logger.info("[AI-v2] [태그 추출 완료]", extra={"tag_count": len(tags)})
        return tags

    except Exception as e:
        ai_logger.exception("[AI-v2] [로컬모델 태그 추출 실패]")
        return []


if __name__ == "__main__":

    sample_text = """
    미야옹즈는 사랑스러운 고양이들과 함께하는 일상을 공유하고, 서로에게 필요한 정보를 나누는 고양이 집사들의 모임입니다.    """
    import asyncio
    async def run_test():
        tags = await extract_tags(sample_text)
        print(tags)
    asyncio.run(run_test())
