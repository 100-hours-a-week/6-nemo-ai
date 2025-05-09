import json
import requests
from datetime import datetime
from src.config import PERSPECTIVE_API_KEY

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

    response = requests.post(PERSPECTIVE_API_URL, json=payload)
    if response.status_code != 200:
        raise Exception(f"Perspective API 오류: {response.status_code} - {response.text}")

    result = {}
    for attr in REQUESTED_ATTRIBUTES:
        try:
            result[attr] = response.json()["attributeScores"][attr]["summaryScore"]["value"]
        except KeyError:
            result[attr] = 0.0  # 값이 없을 경우 0 처리

    return result


def is_request_valid(scores: dict, threshold: float = THRESHOLD) -> bool:
    max_attr, max_score = max(scores.items(), key=lambda x: x[1])
    # print(f"[INFO] 최고 유해성 항목: {max_attr} ({max_score:.3f})")
    return max_score < threshold


# 로그 저장용 함수 (현재는 사용하지 않음)
def log_harmfulness_scores(scores: dict, text: str, log_path: str = "harmfulness_log.jsonl"):
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "text": text.strip(),
        "scores": scores
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    korean_text = """
    이 모임은 멍청한 사람들 모아놓고 얼마나 비효율적인지 관찰하려고 만든 겁니다. 괜히 시간 낭비하지 마시고, 본인 해당되면 그냥 나오세요. 수준 낮은 애들끼리 노는 거예요.
    """

    scores = get_harmfulness_scores_korean(korean_text)
    print("유해성 점수:")
    for k, v in scores.items():
        print(f"  {k}: {v:.3f}")

    # 로그 저장 (현재는 미사용, 주석 해제 시 사용 가능)
    # log_harmfulness_scores(scores, korean_text)

    if not is_request_valid(scores):
        print("해당 모임 요청은 유해성 기준을 초과하여 거부됩니다.")
    else:
        print("해당 모임 요청은 유효합니다.")
