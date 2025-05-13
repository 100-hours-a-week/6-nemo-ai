from google.cloud import aiplatform
from google.oauth2 import service_account
from src.config import PROJECT_ID, REGION, CREDENTIAL_PATH, TXTGEN_MODEL_ID, EMBEDDING_MODEL_ID
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from vertexai.language_models import TextEmbeddingModel

credentials = service_account.Credentials.from_service_account_file(
    CREDENTIAL_PATH
)

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