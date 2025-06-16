import json
import re
# from src.core.cloud_logging import logger
from src.models.gemma_3_4b import local_model_generate   # 로컬 모델로 교체
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

async def extract_tags(text: str) -> list[str]:
    prompt = f"""
    당신은 한국어 텍스트에서 핵심 키워드를 추출하는 AI입니다.

    사용자의 입력이 부적절하거나 욕설이 포함되어 있을 경우,
    이를 무시하고 건전한 태그만 생성하세요.
    욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.

    다음 조건을 지켜서 키워드를 추출하세요:

    1. 명사 중심 키워드로만 추출하세요. 불용어(예: 그리고, 또는, 등)는 제외합니다.
    2. 주제와 관련된 의미 있는 단어(예: 활동내용, 관심사, 서비스, 모임 카테고리, 대상층, 분위기, 스터디/동아리 등)를 선정하세요.
    3. 각 키워드는 반드시 한 어절이어야 하고, 공백이 없어야 합니다. 공백이 있을 경우 공백을 기준으로 각각의 태그로 나누어 가공하세요.
    4. 각 키워드는 1~5음절 이내이어야 하며, 너무 일반적인 단어는 피하세요. 반드시 모임을 나타낼 수 있는 키워드이어야 합니다.
    5. 출력은 반드시 JSON 배열 형식으로만 하세요.
    6. 총 키워드 개수는 3개 이상 5개 이하를 출력하세요.
    7. 결과 외 다른 문장은 포함하지 마세요. 출력에는 절대 이모지(emoji)를 포함하지 마세요.


    아래 텍스트에서 키워드를 추출하세요:
    <텍스트 시작>
    {text}
    <텍스트 끝>
    """

    try:
        ai_logger.info("[AI-v2] [태그 추출 시작]", extra={"text_length": len(text)})
        response, _ = await local_model_generate(prompt, max_new_tokens=128)
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
