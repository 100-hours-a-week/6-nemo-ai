from src.config import HF_TOKEN, HF_API_URL
import requests
#API URL Changes since it's also a work in progress for Hugging Face as well
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
}

def query(payload):
    response = requests.post(HF_API_URL, headers=headers, json=payload)

    # For Debugging
    # print(f"📡 HF 응답 상태코드: {response.status_code}")
    # print(f"📡 응답 내용 일부: {response.text[:100]}")

    if not response.text.strip():
        raise Exception("❌ Hugging Face API 응답이 비어 있음 (빈 문자열)")

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        raise Exception(f"❌ JSON 파싱 실패: {response.text}") from e


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