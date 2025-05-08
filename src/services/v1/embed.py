from src.core.vertex_client import embed_model

def embed(texts: list[str] | str) -> list[list[float]]:
    if isinstance(texts, str):
        texts = [texts]
    elif not isinstance(texts, list):
        raise ValueError("embed 함수는 문자열 또는 문자열 리스트만 지원합니다.")

    embeddings = embed_model.get_embeddings(texts)

    # Vertex SDK는 Embedding 객체 리스트를 반환하므로 `.values` 추출 필요
    return [e.values for e in embeddings]


if __name__ == "__main__":
    import src.core.vertex_client

    texts = [
        "나는 오늘 강남에서 커피를 마셨다.",
        "서울 강남역 근처에는 카페가 정말 많다.",
        "나는 오늘 운동을 하지 못했다."
    ]
    try:
        vectors = embed(texts)
        print(f"임베딩 수: {len(vectors)}")
        print(f"벡터 길이: {len(vectors[0])}")
        print(f"첫 벡터 앞 5개 값: {vectors[0][:5]}")
    except Exception as e:
        print(f"오류 발생: {e}")
