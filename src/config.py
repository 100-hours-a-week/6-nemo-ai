import os
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")
TXTGEN_MODEL_ID = os.getenv("TXTGEN_MODEL_ID")
EMBEDDING_MODEL_ID = os.getenv("EMBED_MODEL_ID")
JSON_FILENAME = os.getenv("CREDENTIAL_PATH")
CREDENTIAL_PATH = os.path.join(PROJECT_ROOT, JSON_FILENAME) #json needs to be on the same directory as the .env file
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


if not PERSPECTIVE_API_KEY:
    raise ValueError("PERSPECTIVE_API_KEY가 .env에 설정되어 있지 않습니다.")
if not PROJECT_ID or not REGION:
    raise ValueError("GCP 설정이 누락되었습니다.")
if not TXTGEN_MODEL_ID or not EMBEDDING_MODEL_ID:
    raise ValueError("모델 ID가 누락되었습니다.")
if not os.path.exists(CREDENTIAL_PATH):
    raise FileNotFoundError(f"인증 JSON 파일이 존재하지 않습니다: {CREDENTIAL_PATH}")
