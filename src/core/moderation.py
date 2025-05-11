import json
import requests
from datetime import datetime, UTC
from src.config import PERSPECTIVE_API_KEY
from src.core.cloud_logging import logger

PERSPECTIVE_API_URL = f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={PERSPECTIVE_API_KEY}"

# 한국어에서 실제 지원되는 속성만 요청
REQUESTED_ATTRIBUTES = {
    "TOXICITY": {},
    "INSULT": {},
    "THREAT": {},
    "IDENTITY_ATTACK": {}
}

THRESHOLD = 0.45  # 유해하다고 판단하는 기준


def get_harmfulness_scores_korean(text: str) -> dict:
    payload = {
        "comment": {"text": text},
        "languages": ["ko"],
        "requestedAttributes": REQUESTED_ATTRIBUTES
    }

    logger.info("[유해성 분석] Perspective API 요청 시작")
    start_time = datetime.now(UTC)

    response = requests.post(PERSPECTIVE_API_URL, json=payload)

    if response.status_code != 200:
        logger.error(f"[유해성 분석][API 오류] 응답 코드: {response.status_code}", exc_info=True)
        raise Exception(f"Perspective API 오류: {response.status_code} - {response.text}")

    try:
        result = {}
        for attr in REQUESTED_ATTRIBUTES:
            result[attr] = response.json()["attributeScores"][attr]["summaryScore"]["value"]

        latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        logger.info(f"[유해성 분석] 응답 파싱 성공 - 처리시간: {latency_ms}ms")
        return result

    except KeyError:
        logger.error("[유해성 분석][파싱 오류] 응답에서 키 누락", exc_info=True)
        raise

def is_request_valid(scores: dict, threshold: float = THRESHOLD) -> bool:
    max_attr, max_score = max(scores.items(), key=lambda x: x[1])
    logger.info(f"[유해성 분석] 최대 유해 점수: {max_attr}({max_score:.3f})")
    return max_score < threshold


# 로그 저장용 함수
def log_harmfulness_scores(scores: dict, text: str, log_path: str = "harmfulness_log.jsonl"):
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "text": text.strip(),
        "scores": scores
    }



if __name__ == "__main__":
    korean_text = """
    이 모임은 멍청한 사람들 모아놓고 얼마나 비효율적인지 관찰하려고 만든 겁니다. 괜히 시간 낭비하지 마시고, 본인 해당되면 그냥 나오세요. 수준 낮은 애들끼리 노는 거예요.
    """

    logger.info("[테스트 실행] 유해성 분석 샘플 시작")
    scores = get_harmfulness_scores_korean(korean_text)

    logger.info("[테스트 실행] 유해성 점수 결과", extra={"scores": scores})

    if not is_request_valid(scores):
        logger.warning("[테스트 실행] 유해성 기준 초과로 요청 거부됨")
    else:
        logger.info("[테스트 실행] 요청 유효함")