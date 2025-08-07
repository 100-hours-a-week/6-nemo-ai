import json
import re
# from app.core.cloud_logging import logger
from app.core.vertex_client import smart_generate
from app.core.ai_logger import get_ai_logger
from app.prompts.prompt_loader import load_prompt_template

ai_logger = get_ai_logger()

async def extract_tags(text: str) -> list[str]:
    prompt = load_prompt_template("tag_extraction", "v1", text=text)

    try:
        ai_logger.info("[AI] [태그 추출 시작]", extra={"text_length": len(text)})
        response = await smart_generate(prompt)
        raw = response.strip()

        try:
            tags = json.loads(raw)
        except json.JSONDecodeError:
            ai_logger.info("[AI] [JSON 파싱 실패] 태그 정규식으로 대체 처리", extra={"raw_preview": raw[:80]})
            tags = re.findall(r'"(.*?)"', raw)

        ai_logger.info("[AI] [태그 추출 완료]", extra={"tag_count": len(tags)})
        return tags

    except Exception as e:
        ai_logger.exception("[AI] [Vertex Gemini 태그 추출 실패]")
        return []


if __name__ == "__main__":

    sample_text = """
    네모는 개발자와 디자이너가 함께 모여 사이드 프로젝트를 진행하는 커뮤니티입니다.
    매주 오프라인에서 아이디어를 공유하고, 코드 리뷰와 디자인 피드백 세션을 통해 서로 성장합니다.
    관심 분야는 웹 개발, 인공지능, UX/UI 디자인입니다.
    """
    import asyncio
    async def run_test():
        tags = await extract_tags(sample_text)
        print(tags)
    asyncio.run(run_test())
