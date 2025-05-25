from sentence_transformers import SentenceTransformer, util

# 모델 로딩 (CPU 기반)
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# 후보 태그(사전 정의된 개념)
tag_candidates = [
    "AI", "딥러닝", "머신러닝", "스터디", "자기계발", "네트워크", "자연어처리", "비즈니스", "프로젝트"
]
# 각 태그에 대해 임베딩 미리 계산
tag_embeddings = model.encode(tag_candidates, convert_to_tensor=True)

def get_embedding(text: str):
    embedding = model.encode(text, convert_to_tensor=True)
    return embedding.tolist()  # JSON 직렬화를 위해 list로 변환

# 태그 추출 예시 (실제 서비스에서는 벡터 기반 추천 또는 분류로 대체)
def extract_tags(text: str):
    # 입력 문장 임베딩
    input_embedding = model.encode(text, convert_to_tensor=True)

    # cosine similarity 계산
    similarities = util.pytorch_cos_sim(input_embedding, tag_embeddings)[0]

    # 유사도 높은 상위 3개 인덱스 추출
    top_k = min(3, len(tag_candidates))
    top_indices = similarities.topk(top_k).indices

    # 해당 인덱스의 태그 반환
    return [tag_candidates[i] for i in top_indices]