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

# Discord Configuration
DISCORD_ENABLED = os.getenv("DISCORD_ENABLED", "false").lower() == "true"
DISCORD_LOG_LEVEL = os.getenv("DISCORD_LOG_LEVEL", "WARNING").upper()

APP_ENV = os.getenv("APP_ENV", "development")
CHROMA_DB_PATH = str((BASE_DIR / "database" / APP_ENV).resolve())
EMBED_MODEL = os.getenv("EMBED_MODEL_NAME")

#MySQL
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
DB_USER = os.getenv("DB_USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")

vLLM_URL = os.getenv("VLLM_API_URL", "http://localhost:8001")

# vLLM Configuration
VLLM_TIMEOUT = int(os.getenv("VLLM_TIMEOUT", "30"))
VLLM_STREAM_TIMEOUT = int(os.getenv("VLLM_STREAM_TIMEOUT", "120"))
VLLM_READ_TIMEOUT = int(os.getenv("VLLM_READ_TIMEOUT", "60"))
VLLM_MAX_RETRIES = int(os.getenv("VLLM_MAX_RETRIES", "3"))

# vLLM Model Configuration
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "gemma-3-4b-it")
VLLM_MAX_TOKENS = int(os.getenv("VLLM_MAX_TOKENS", "512"))
VLLM_TEMPERATURE = float(os.getenv("VLLM_TEMPERATURE", "0.7"))
VLLM_GPU_MEMORY_UTIL = float(os.getenv("VLLM_GPU_MEMORY_UTIL", "0.8"))

KAFKA_BOOTSTRAP_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVER", "localhost:9092")
KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "true").lower() == "true"

# Kafka Consumer Configuration
KAFKA_CONSUMER_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP_ID", "ai-recommender-group")
KAFKA_MAX_POLL_RECORDS = int(os.getenv("KAFKA_MAX_POLL_RECORDS", "10"))
KAFKA_SESSION_TIMEOUT_MS = int(os.getenv("KAFKA_SESSION_TIMEOUT_MS", "30000"))
KAFKA_HEARTBEAT_INTERVAL_MS = int(os.getenv("KAFKA_HEARTBEAT_INTERVAL_MS", "10000"))
KAFKA_MAX_POLL_INTERVAL_MS = int(os.getenv("KAFKA_MAX_POLL_INTERVAL_MS", "300000"))

if not PERSPECTIVE_API_KEY:
    raise ValueError("PERSPECTIVE_API_KEY가 .env에 설정되어 있지 않습니다.")

# Discord validation
if DISCORD_ENABLED and not WEBHOOK_URL:
    raise ValueError("DISCORD_ENABLED가 활성화되었지만 WEBHOOK_URL이 설정되어 있지 않습니다.")

# if not EMBED_MODEL:
#     raise ValueError("EMBED_MODEL이 .env에 설정되어 있지 않습니다.")
# if not PROJECT_ID or not REGION:
#     raise ValueError("GCP 설정이 누락되었습니다.")
# if not TXTGEN_MODEL_ID or not EMBEDDING_MODEL_ID:
#     raise ValueError("모델 ID가 누락되었습니다.")

