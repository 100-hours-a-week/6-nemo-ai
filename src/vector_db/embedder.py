import torch
from typing import List, Union
from sentence_transformers import SentenceTransformer
from chromadb.api.types import EmbeddingFunction
from src.config import EMBED_MODEL
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

class JinaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name: str = EMBED_MODEL):
        self._model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, trust_remote_code=True).to(self.device)
        ai_logger.info(f"[AI] [임베딩 모델 로드 완료]: {model_name} ({self.device})")

    def __call__(self, input: Union[List[str], str]) -> List[List[float]]:
        if isinstance(input, str):
            input = [input]
        elif not isinstance(input, list):
            raise ValueError("입력은 문자열 또는 문자열 리스트여야 합니다.")

        try:
            ai_logger.info("[AI] [임베딩 요청]", extra={"input_count": len(input)})

            vectors = self.model.encode(input, convert_to_numpy=True).tolist()

            if len(vectors) != len(input):
                ai_logger.warning("[AI] [임베딩 수 불일치]", extra={
                    "input_count": len(input), "output_count": len(vectors)
                })

            ai_logger.info("[AI] [임베딩 완료]", extra={"vector_dim": len(vectors[0]) if vectors else 0})
            return vectors

        except Exception:
            ai_logger.exception("[AI] [임베딩 실패]")
            return []

    def name(self) -> str:
        return self._model_name

if __name__ == "__main__":
    emb = JinaEmbeddingFunction()
    print("[임베딩 차원 확인]", len(emb(["test"])[0]))