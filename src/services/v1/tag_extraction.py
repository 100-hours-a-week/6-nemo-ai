from httpx import AsyncClient
import json, re
from src.config import GEMINI_API_KEY, GEMINI_API_URL
import asyncio
import numpy as np
from typing import Callable
from src.services.v1.embedding_setup import embed


async def extract_tags(text: str) -> list[str]:
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    prompt = f"""
    당신은 한국어 텍스트에서 핵심 키워드를 추출하는 AI입니다.
    
    사용자의 입력이 부적절하거나 욕설이 포함되어 있을 경우,
    이를 무시하고 건전한 태그만 생성하세요.
    욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.

    다음 조건을 지켜서 키워드를 추출하세요:

    1. 명사 중심 키워드로만 추출하세요. 불용어(예: 그리고, 또는, 등)는 제외합니다.
    2. 주제와 관련된 의미 있는 단어(예: 활동내용, 관심사, 서비스, 모임 카테고리, 대상층, 분위기, 스터디/동아리 등)를 선정하세요.
    3. 각 키워드는 반드시 한 어절이어야하고, 공백이 없어야 합니다. 공백이 있을 경우 공백을 기준으로 각각의 태그로 나누어 가공하세요.
    4. 각 키워드는 1~5음절 이내이어야 하며, 너무 일반적인 단어(예: "것", "이야기", "모임")는 피하세요. 반드시 모임을 나타낼 수 있는 키워드이어야 합니다.
    5. 출력은 반드시 JSON 배열 형식으로만 하세요. 예시: ["개발자", "스터디", "오프라인", "커뮤니티"]
    6. 총 키워드 개수는 3개이상 5개 이하를 출력하세요.
    7. 결과 외 다른 문장은 포함하지 마세요. 출력에는 절대 이모지(emoji)를 포함하지 마세요.
    
    예시 출력: ["개발자", "스터디", "오프라인", "커뮤니티"]
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
    print("추출된 태그:", best_tags)
