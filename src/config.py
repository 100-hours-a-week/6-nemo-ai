import os
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
PERSPECTIVE_API_KEY = os.getenv("PERSPECTIVE_API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("REGION")
TXTGEN_MODEL_ID = os.getenv("TXTGEN_MODEL_ID")
EMBEDDING_MODEL_ID = os.getenv("EMBED_MODEL_ID")
CREDENTIAL_PATH = os.getenv("CREDENTIAL_PATH")

# if not NGROK_AUTH_TOKEN:
#     raise ValueError("No Ngrok Auth Token found. Set it in the .env file.")
#if not PERSPECTIVE_API_KEY:
#    raise ValueError("No Perspective API Key found. Set it in the .env file.")
