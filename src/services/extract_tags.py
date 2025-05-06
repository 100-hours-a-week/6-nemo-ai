from httpx import AsyncClient
import json, re
from src.config import GEMINI_API_KEY, GEMINI_API_URL
import asyncio
import numpy as np
from typing import Callable
from src.services.hf_api_setup_v1 import embed


async def extract_tags(text: str) -> list[str]:
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    prompt = f"""
    당신은 한국어 텍스트에서 핵심 키워드를 추출하는 AI입니다.

    다음 조건을 지켜서 키워드를 추출하세요:

    1. 명사 중심 키워드로만 추출하세요. 불용어(예: 그리고, 또는, 등)는 제외합니다.
    2. 주제와 관련된 의미 있는 단어(예: 활동, 관심사, 서비스, 개발자 스터디 등)를 선정하세요. 각 키워드는 공백 대신 '_'로 태그 형태로 가공하세요.
    3. 각 키워드는 1~5어절 이내의 짧은 구문이어야 하며, 너무 일반적인 단어(예: "것", "이야기")는 피하세요.
    4. 출력은 반드시 JSON 배열 형식으로만 하세요. 예시: ["개발자_스터디", "오프라인_밋업", "커뮤니티_모임"]
    5. 총 키워드 3개~5개를 출력하세요.
    6. 결과 외 다른 문장은 포함하지 마세요. 
    예시 출력: ["개발자_스터디", "오프라인_밋업", "커뮤니티_모임"]

    아래 텍스트에서 키워드를 추출하세요:

    <텍스트 시작>
    {text}
    <텍스트 끝>
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "candidateCount": 5,
            "temperature": 0.8,  # 다양성 증가
            "topK": 40,  # 상위 40개 중 샘플
            "topP": 0.9  # 누적 확률 90% 내에서 샘플
        }
    }

    try:
        async with AsyncClient() as client:
            response = await client.post(GEMINI_API_URL, headers=headers, params=params, json=payload)
            response.raise_for_status()

            # 수정된 부분: try-except로 json 파싱 안전하게 처리
            try:
                res = await response.json()
            except Exception:
                res = json.loads(response.text)

            outputs = []
            for c in res.get("candidates", []):
                try:
                    raw = c["content"]["parts"][0]["text"].strip()
                    tags = json.loads(raw)
                except json.JSONDecodeError:
                    tags = re.findall(r'"(.*?)"', raw)
                outputs.append(tags)

            return outputs

    except Exception as e:
        print(f"[Gemini 태그 추출 실패] {str(e)}")
        return []

def pick_best_by_vector_similarity(candidates: list[list[str]], base_text: str, embed_fn: Callable[[list[str] | str], list[list[float]]]) -> list[str]:
    """
    주어진 태그 후보들 중 base_text와 가장 유사한 태그 리스트를 선택합니다.

    Parameters:
    - candidates: [["개발자_스터디", ...], [...], ...] 형식의 태그 리스트 후보
    - base_text: 비교 기준이 되는 문장
    - embed_fn: 텍스트 리스트를 벡터로 임베딩하는 함수

    Returns:
    - 가장 유사도가 높은 태그 리스트 (list[str])
    """

    # 후보 태그들을 문자열로 평탄화 (벡터 모델 입력용)
    candidate_texts = [" ".join(tags) for tags in candidates]

    # 기준 문장 + 후보 태그 리스트들 함께 임베딩
    all_texts = [base_text] + candidate_texts
    embeddings = embed_fn(all_texts)  # [[벡터], [벡터], ...]

    base_vec = np.array(embeddings[0])
    candidate_vecs = [np.array(vec) for vec in embeddings[1:]]

    # cosine similarity 계산
    similarities = [
        np.dot(base_vec, vec) / (np.linalg.norm(base_vec) * np.linalg.norm(vec) + 1e-8)
        for vec in candidate_vecs
    ]

    # 가장 높은 유사도 인덱스
    best_idx = int(np.argmax(similarities))
    return candidates[best_idx]

if __name__ == "__main__":
    sample_text = """
    네모는 개발자와 디자이너가 함께 모여 사이드 프로젝트를 진행하는 커뮤니티입니다.
    매주 오프라인에서 아이디어를 공유하고, 코드 리뷰와 디자인 피드백 세션을 통해 서로 성장합니다.
    관심 분야는 웹 개발, 인공지능, UX/UI 디자인입니다.
    """
    result = asyncio.run(extract_tags(sample_text))
    print(result)
    best_tags = pick_best_by_vector_similarity(result, sample_text, embed_fn=embed)
    print("📌 추출된 태그:", best_tags)
