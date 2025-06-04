import torch
from sentence_transformers import SentenceTransformer
from src.config import EMBED_MODEL
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer(EMBED_MODEL, trust_remote_code=True).to(device)

def embed(texts: list[str] | str) -> list[list[float]]:
    if isinstance(texts, str):
        texts = [texts]
    elif not isinstance(texts, list):
        raise ValueError("embed 함수는 문자열 또는 문자열 리스트만 지원합니다.")

    try:
        ai_logger.info("[AI] [임베딩 요청]", extra={"input_count": len(texts)})

        # 임베딩 수행
        vectors = model.encode(texts, convert_to_numpy=True).tolist()

        if len(vectors) != len(texts):
            ai_logger.warning("[AI] [임베딩 수 불일치]", extra={"input_count": len(texts), "output_count": len(vectors)})

        ai_logger.info("[AI] [임베딩 완료]", extra={"vector_dim": len(vectors[0]) if vectors else 0})
        return vectors

    except Exception:
        ai_logger.exception("[AI] [임베딩 실패]")
        return []

if __name__ == "__main__":
    print("[임베딩 차원 확인]", len(model.encode(["test"], convert_to_numpy=True)[0]))