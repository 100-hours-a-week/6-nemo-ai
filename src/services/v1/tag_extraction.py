import json
import re
from src.core.vertex_client import gen_model
from src.core.logging_config import logger

def extract_tags(text: str) -> list[str]:
    prompt = f"""
    당신은 한국어 텍스트에서 핵심 키워드를 추출하는 AI입니다.

    사용자의 입력이 부적절하거나 욕설이 포함되어 있을 경우,
    이를 무시하고 건전한 태그만 생성하세요.
    욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.

    다음 조건을 지켜서 키워드를 추출하세요:

    1. 명사 중심 키워드로만 추출하세요. 불용어(예: 그리고, 또는, 등)는 제외합니다.
    2. 주제와 관련된 의미 있는 단어(예: 활동내용, 관심사, 서비스, 모임 카테고리, 대상층, 분위기, 스터디/동아리 등)를 선정하세요.
    3. 각 키워드는 반드시 한 어절이어야 하고, 공백이 없어야 합니다. 공백이 있을 경우 공백을 기준으로 각각의 태그로 나누어 가공하세요.
    4. 각 키워드는 1~5음절 이내이어야 하며, 너무 일반적인 단어(예: "것", "이야기", "모임")는 피하세요. 반드시 모임을 나타낼 수 있는 키워드이어야 합니다.
    5. 출력은 반드시 JSON 배열 형식으로만 하세요. 예시: ["개발자", "스터디", "오프라인", "커뮤니티"]
    6. 총 키워드 개수는 3개 이상 5개 이하를 출력하세요.
    7. 결과 외 다른 문장은 포함하지 마세요. 출력에는 절대 이모지(emoji)를 포함하지 마세요.

    예시 출력: ["개발자", "스터디", "오프라인", "커뮤니티"]

    아래 텍스트에서 키워드를 추출하세요:
    <텍스트 시작>
    {text}
    <텍스트 끝>
    """

    response = gen_model.generate_content(prompt)
    raw = response.text.strip()

    try:
        logger.info("[태그 추출 시작]", extra={"text_length": len(text)})
        response = gen_model.generate_content(prompt)
        raw = response.text.strip()

        try:
            tags = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[JSON 파싱 실패] 정규식으로 대체 처리", extra={"raw_preview": raw[:80]})
            tags = re.findall(r'"(.*?)"', raw)

        logger.info("[태그 추출 완료]", extra={"tag_count": len(tags)})
        return tags

    except Exception as e:
        logger.exception("[Vertex Gemini 태그 추출 실패]")
        return []


if __name__ == "__main__":

    sample_text = """
    네모는 개발자와 디자이너가 함께 모여 사이드 프로젝트를 진행하는 커뮤니티입니다.
    매주 오프라인에서 아이디어를 공유하고, 코드 리뷰와 디자인 피드백 세션을 통해 서로 성장합니다.
    관심 분야는 웹 개발, 인공지능, UX/UI 디자인입니다.
    """
    tags = extract_tags(sample_text)
    print(tags)
