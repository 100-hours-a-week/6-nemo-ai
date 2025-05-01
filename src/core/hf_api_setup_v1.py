from config import HF_TOKEN
import requests

API_URL = "https://router.huggingface.co/hf-inference/pipeline/sentence-similarity/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"Status code: {response.status_code}")
        print(f"Response text: {response.text}")
        raise e

def embed(texts: list[str]) -> list[list[float]]:
    embeddings = []
    for text in texts:
        res = requests.post(API_URL, headers=headers, json={"inputs": text})
        if res.status_code != 200:
            raise Exception(f"HF API Error: {res.status_code} | {res.text}")
        embeddings.append(res.json()[0])
    return embeddings

if __name__ == "__main__":
    output = query({
        "inputs": {
        "source_sentence": "그 사람은 행복한 사람이다",
        "sentences": [
            "행복한 강아지네요",
            "정말 행복한 사람이네요",
            "오늘은 날씨가 맑네요"
        ]
    },
    })

    print(output)