from typing import List, Union
from sentence_transformers import SentenceTransformer
from chromadb.api.types import EmbeddingFunction
from app.config import EMBED_MODEL
from app.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()
_MODEL = SentenceTransformer(EMBED_MODEL, trust_remote_code=True).to("cpu")

class E5EmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name: str = EMBED_MODEL):
        self._model_name = model_name
        self.device = "cpu"
        self.model = _MODEL
        ai_logger.info(f"[AI] [임베딩 모델 로드 완료]: {model_name} ({self.device})")

    def __call__(self, input: Union[List[str], str]) -> List[List[float]]:
        if isinstance(input, str):
            input = [input]
        elif not isinstance(input, list):
            raise ValueError("입력은 문자열 또는 문자열 리스트여야 합니다.")

        try:
            ai_logger.info("[AI] [임베딩 요청]", extra={"input_count": len(input)})

            # E5 models benefit from query prefixes for better performance
            # For general text embedding, we can use "passage: " prefix
            prefixed_input = [f"passage: {text}" for text in input]
            
            vectors = self.model.encode(prefixed_input, convert_to_numpy=True).tolist()

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

embed = E5EmbeddingFunction()

if __name__ == "__main__":
    print("[임베딩 차원 확인]", len(embed(["test"])[0]))
