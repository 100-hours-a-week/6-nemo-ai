import json
import re
# from src.core.cloud_logging import logger
#from src.services.v2.local_model import local_model_generate   # 로컬 모델로 교체
from src.models.tgi_client import tgi_generate
from src.core.ai_logger import get_ai_logger
import asyncio

ai_logger = get_ai_logger()

async def extract_tags(text: str) -> list[str]:
    prompt = f"""
    당신은 입력된 한국어 텍스트를 분석하여, 모임의 주제나 성격을 가장 잘 표현하는 핵심 키워드만을 정제하여 JSON 배열 형태로 추출하는 AI 태그 생성기입니다.

    사용자의 입력이 부적절하거나 욕설이 포함되어 있을 경우,
    이를 무시하고 건전한 태그만 생성하세요.
    욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.

    다음 조건을 지켜서 키워드를 추출하세요:

    1. 모든 키워드는 의미 있는 명사 단어로만 구성되어야 합니다.
    2. 불용어(예: 그리고, 또는, 이다 등)와 욕설/비하/부적절 표현은 제거합니다.
    3. 각 키워드는 공백 없는 단일 어절이어야 하며, 공백이 있다면 단어를 분할하여 별도 키워드로 추출하세요.
    4. 키워드는 1~5음절 이내로 제한하고, 너무 일반적인 단어(예: 모임, 사람, 활동 등)는 제외하세요.
    5. 태그는 JSON 배열 형식으로만 출력하며, 총 3개 이상 5개 이하를 생성합니다.
    6. 출력에는 절대 이모지, 기호, 문장 설명을 포함하지 마세요.
    7. 모든 태그는 중복되지 않아야 하며, 숫자나 기호로만 이루어진 단어는 제외합니다.

    아래 텍스트에서 키워드를 추출하세요:
    <텍스트 시작>
    {text}
    <텍스트 끝>
    """

    try:
        ai_logger.info("[AI-v2] [태그 추출 시작]", extra={"text_length": len(text)})
        response, _ = await tgi_generate(prompt, max_new_tokens=128)
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
    백엔드 개발에 관심 있는 사람들과 함께 기술 블로그를 운영하며, 실습 중심으로 성장하는 개발자 스터디입니다.
    """
    import asyncio
    async def run_test():
        tags = await extract_tags(sample_text)
        print(tags)
    asyncio.run(run_test())
