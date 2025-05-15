import json
import requests
from datetime import datetime, UTC
from src.config import PERSPECTIVE_API_KEY
from src.core.ai_logger import get_ai_logger
import asyncio

ai_logger = get_ai_logger()

PERSPECTIVE_API_URL = (
    f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={PERSPECTIVE_API_KEY}"
)

REQUESTED_ATTRIBUTES = {
    "TOXICITY": {},
    "INSULT": {},
    "THREAT": {},
    "IDENTITY_ATTACK": {}
}

THRESHOLD = 0.45

def get_harmfulness_scores_korean(text: str) -> dict:
    payload = {
        "comment": {"text": text},
        "languages": ["ko"],
        "requestedAttributes": REQUESTED_ATTRIBUTES
    }

    ai_logger.info("[AI] [Moderation 시작] Perspective API 요청", extra={"text_length": len(text)})
    start_time = datetime.now(UTC)

    response = requests.post(PERSPECTIVE_API_URL, json=payload)

    if response.status_code != 200:
        ai_logger.error("[AI] [Moderation 실패] 응답 코드 오류", extra={"status_code": response.status_code})
        raise Exception(f"Perspective API 오류: {response.status_code} - {response.text}")

    try:
        result = {
            attr: response.json()["attributeScores"][attr]["summaryScore"]["value"]
            for attr in REQUESTED_ATTRIBUTES
        }

        latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        ai_logger.info("[AI] [Moderation 성공] 유해성 점수 파싱 완료", extra={
            "latency_ms": latency_ms,
            "scores": result
        })
        return result

    except KeyError:
        ai_logger.error("[AI] [Moderation 파싱 실패] 응답 키 누락", exc_info=True)
        raise

def is_request_valid(scores: dict, threshold: float = THRESHOLD) -> bool:
    max_attr, max_score = max(scores.items(), key=lambda x: x[1])
    if max_score >= threshold:
        ai_logger.warning("[AI] [Moderation 평가] 유해성 기준 초과", extra={
            "attribute": max_attr,
            "score": round(max_score, 3),
            "threshold": threshold
        })

    return max_score < threshold

perspective_lock = asyncio.Semaphore(1)

async def analyze_queued(text: str) -> dict:
    async with perspective_lock:
        try:
            return get_harmfulness_scores_korean(text)
        except Exception as e:
            ai_logger.warning("[AI] [Moderation fallback] 기본 점수 반환", extra={"error": str(e)})
            return {
                "TOXICITY": 0.0,
                "INSULT": 0.0,
                "THREAT": 0.0,
                "IDENTITY_ATTACK": 0.0
            }

if __name__ == "__main__":
    test_text = "이 모임은 멍청한 사람들 모아놓고 얼마나 비효율적인지 관찰하려고 만든 겁니다."

    print(f"입력 텍스트:\n{test_text}\n")

    try:
        scores = get_harmfulness_scores_korean(test_text)
        is_valid = is_request_valid(scores)

        print("유해성 점수:")
        for attr, value in scores.items():
            print(f"- {attr}: {value:.3f}")

        print(f"\n유해한 콘텐츠인가요? {'아니오 (허용)' if is_valid else '예 (차단)'}")

    except Exception as e:
        print(f"에러 발생: {e}")
