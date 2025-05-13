from google.cloud import aiplatform
from google.oauth2 import service_account
from src.config import PROJECT_ID, REGION, CREDENTIAL_PATH, TXTGEN_MODEL_ID, EMBEDDING_MODEL_ID
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from vertexai.language_models import TextEmbeddingModel
from src.core.cache_local import make_cache_key, get_cached, set_cached

credentials = service_account.Credentials.from_service_account_file(
    CREDENTIAL_PATH
)

def generate_with_cache(prompt: str, model_name: str = TXTGEN_MODEL_ID) -> dict:

    key = make_cache_key("vertex", prompt, model_name)
    cached = get_cached(key)
    if cached:
        return cached

    try:
        response = gen_model.generate_content(prompt, generation_config=config_model)
        result = {"text": response.text}
    except Exception:
        result = {"text": "일시적인 오류입니다. 잠시 후 다시 시도해주세요."}  # fallback

    set_cached(key, result)
    return result

aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    credentials=credentials
)

gen_model = GenerativeModel(TXTGEN_MODEL_ID)
embed_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_ID)
config_model = GenerationConfig(
        temperature=0.75,
        top_p=0.95,
        top_k=40,
        max_output_tokens=900,
    )