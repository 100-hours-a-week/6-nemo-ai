from src.config import HF_TOKEN
import requests

API_URL = "https://router.huggingface.co/hf-inference/pipeline/feature-extraction/BAAI/bge-large-zh-v1.5"
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)

    # print(f"📡 HF 응답 상태코드: {response.status_code}")
    # print(f"📡 응답 내용 일부: {response.text[:100]}")

    if not response.text.strip():
        raise Exception("❌ Hugging Face API 응답이 비어 있음 (빈 문자열)")

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        raise Exception(f"❌ JSON 파싱 실패: {response.text}") from e



def embed(texts: list[str]) -> list[list[float]]:
    response = query({"inputs": texts})

    if not response:
        raise Exception("❌ Empty response from HF API.")
    if isinstance(response, dict) and "error" in response:
        raise Exception(f"❌ HF API Error: {response['error']}")

    if not isinstance(response, list) or not isinstance(response[0], list):
        raise Exception(f"❌ Unexpected embedding format: {response}")

    return response


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