from src.config import HF_TOKEN, HF_API_URL
import requests
import time
import logging
#NOTE: API URL Changes since it's also a work in progress for Hugging Face as well (503 call happens often)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
}

fallback_vector = [[0.0] * 384]  # 임베딩 차원 수에 따라 조절

def query(payload, max_retries=3, backoff_factor=2):
    for attempt in range(max_retries):
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 503:
                wait = backoff_factor ** attempt
                logger.warning(f"⚠️ 503 Service Unavailable - Retrying in {wait} seconds ({attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                logger.error(f"❌ 요청 실패: {response.status_code} - {response.text}")
                break  # 4xx나 다른 오류면 재시도하지 않음
        except Exception as e:
            logger.exception("❌ 예외 발생 중 요청 실패")
            break

    logger.error("❌ 최대 재시도 횟수 초과 또는 복구 불가능한 오류 - fallback 벡터 사용")
    return fallback_vector  # or raise Exception if fallback이 아닌 실패 처리 원할 경우

def embed(texts: list[str] | str) -> list[list[float]]:
    # 문자열 단일 입력 시 리스트로 변환
    if isinstance(texts, str):
        texts = [texts]
    elif not isinstance(texts, list):
        raise ValueError("embed 함수는 문자열 또는 문자열 리스트만 지원합니다.")

    response = query({"inputs": texts})

    if not response:
        raise Exception("❌ Empty response from HF API.")
    if isinstance(response, dict) and "error" in response:
        raise Exception(f"❌ HF API Error: {response['error']}")

    # Hugging Face API는 단일 문장일 경우 1D vector 반환 가능
    if isinstance(response[0], float):  # 단일 벡터 (1D)일 경우
        return [response]  # 2D로 감싸서 일관된 형태로 반환
    elif isinstance(response, list) and isinstance(response[0], list):
        return response
    else:
        raise Exception(f"❌ Unexpected embedding format: {response}")



if __name__ == "__main__":
    texts = [
        "나는 오늘 강남에서 커피를 마셨다.",
        "서울 강남역 근처에는 카페가 정말 많다.",
        "나는 오늘 운동을 하지 못했다."
    ]
    try:
        vectors = embed(texts)
        print(f"✅ 임베딩 수: {len(vectors)}")
        print(f"✅ 벡터 길이: {len(vectors[0])}")
        print(f"✅ 첫 벡터 앞 5개 값: {vectors[0][:5]}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")