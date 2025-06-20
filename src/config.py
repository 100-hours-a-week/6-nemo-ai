import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).resolve().parent.parent

NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")

PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")
TXTGEN_MODEL_ID = os.getenv("TXTGEN_MODEL_ID")
EMBEDDING_MODEL_ID = os.getenv("EMBED_MODEL_ID")
JSON_FILENAME = os.getenv("CREDENTIAL_PATH")
CREDENTIAL_PATH = os.path.join(BASE_DIR, JSON_FILENAME) #json needs to be on the same directory as the .env file

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

APP_ENV = os.getenv("APP_ENV", "development")
CHROMA_DB_PATH = str((BASE_DIR / "database" / APP_ENV).resolve())
EMBED_MODEL = os.getenv("EMBED_MODEL_NAME")

#MySQL
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")

vLLM_URL = os.getenv("VLLM_API_URL")


if not PERSPECTIVE_API_KEY:
    raise ValueError("PERSPECTIVE_API_KEY가 .env에 설정되어 있지 않습니다.")

# if not EMBED_MODEL:
#     raise ValueError("EMBED_MODEL이 .env에 설정되어 있지 않습니다.")
# if not PROJECT_ID or not REGION:
#     raise ValueError("GCP 설정이 누락되었습니다.")
# if not TXTGEN_MODEL_ID or not EMBEDDING_MODEL_ID:
#     raise ValueError("모델 ID가 누락되었습니다.")

