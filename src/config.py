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
CREDENTIAL_PATH = os.path.join(PROJECT_ROOT, JSON_FILENAME)



# if not NGROK_AUTH_TOKEN:
#     raise ValueError("No Ngrok Auth Token found. Set it in the .env file.")
#if not PERSPECTIVE_API_KEY:
#    raise ValueError("No Perspective API Key found. Set it in the .env file.")
