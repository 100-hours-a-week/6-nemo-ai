import json
import requests
from datetime import datetime, UTC
from src.config import PERSPECTIVE_API_KEY
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

PERSPECTIVE_API_URL = f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={PERSPECTIVE_API_KEY}"

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
        ai_logger.info("[AI] [Moderation 성공] 유해성 점수 파싱 완료", extra={"latency_ms": latency_ms, "scores": result})
        return result

    except KeyError:
        ai_logger.error("[AI] [Moderation 파싱 실패] 응답 키 누락", exc_info=True)
        raise

def is_request_valid(scores: dict, threshold: float = THRESHOLD) -> bool:
    max_attr, max_score = max(scores.items(), key=lambda x: x[1])
    ai_logger.info("[AI] [Moderation 평가] 최대 유해 점수", extra={"attribute": max_attr, "score": max_score})
    return max_score < threshold

def log_harmfulness_scores(scores: dict, text: str, log_path: str = "harmfulness_log.jsonl"):
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "text": text.strip(),
        "scores": scores
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
    ai_logger.info("[AI] [Moderation 저장] JSONL 로그 기록됨", extra={"log_path": log_path})
