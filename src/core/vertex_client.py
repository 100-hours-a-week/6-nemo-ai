import asyncio
from google.cloud import aiplatform
from google.oauth2 import service_account
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from vertexai.language_models import TextEmbeddingModel
from google.api_core.exceptions import InvalidArgument, ResourceExhausted
from src.config import PROJECT_ID, REGION, CREDENTIAL_PATH, TXTGEN_MODEL_ID, EMBEDDING_MODEL_ID
from src.core.ai_logger import get_ai_logger
from src.core.rate_limiter import RateLimitedExecutor, QueuedExecutor

# --- 로깅 설정
ai_logger = get_ai_logger()

# --- 인증 및 Vertex AI 초기화 (최초 1회만 실행됨, import시 캐싱)
credentials = service_account.Credentials.from_service_account_file(CREDENTIAL_PATH)

aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    credentials=credentials,
)

# --- 모델 로딩 (전역 캐시)
gen_model = GenerativeModel(TXTGEN_MODEL_ID)
embed_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_ID)

# --- 생성 설정
config_model = GenerationConfig(
    temperature=0.75,
    top_p=0.95,
    top_k=40,
    max_output_tokens=900,
)

# --- 제한된 실행 환경 (QPS, worker 제한 포함)
vertex_executor = RateLimitedExecutor(max_workers=3, qps=1)
queued_executor = QueuedExecutor(max_workers=3, qps=1)

# --- 동기 호출 함수 (기본)
def generate_content(prompt: str) -> str:
    try:
        response = gen_model.generate_content(prompt, generation_config=config_model)

        if not response.text or not response.text.strip():
            ai_logger.warning("[AI] [VertexAI Empty Response]", extra={"prompt": prompt[:100]})
            return "[EMPTY]"

        return response.text

    except InvalidArgument as e:
        ai_logger.warning("[AI] [VertexAI InvalidArgument]", extra={"error": str(e), "prompt": prompt[:100]})
        return "[INVALID_ARGUMENT]"

    except ResourceExhausted as e:
        ai_logger.warning("[AI] [VertexAI QuotaExceeded]", extra={"error": str(e), "prompt": prompt[:100]})
        return "[QUOTA_EXCEEDED]"

    except Exception as e:
        ai_logger.warning("[AI] [VertexAI Error]", extra={"error": str(e), "prompt": prompt[:100]})
        return "[ERROR]"

# --- 제한된 동기 실행 (CLI/동기 환경에서 사용)
def limited_generate(prompt: str) -> str:
    ai_logger.info("[AI] [VertexAI 요청 시작]", extra={"prompt": prompt[:80]})
    future = vertex_executor.submit(generate_content, prompt)
    result = future.result()
    ai_logger.info("[AI] [VertexAI 요청 완료]", extra={"result_preview": result[:80]})
    return result

# --- 스마트 비동기 호출 (async 환경에서도 안전, 자동 판단)
async def smart_generate(prompt: str) -> str:
    try:
        loop = asyncio.get_running_loop()
        return await queued_executor.submit(generate_content, prompt)
    except RuntimeError:
        return await asyncio.run(queued_executor.submit(generate_content, prompt))
