import os
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)
HF_TOKEN = os.getenv("HF_TOKEN")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")

if not HF_TOKEN:
    raise ValueError("No HuggingFace key found. Set it in the .env file.")
if not NGROK_AUTH_TOKEN:
    raise ValueError("No Ngrok Auth Token found. Set it in the .env file.")
if not GEMINI_KEY:
    raise ValueError("No Gemini Key found. Set it in the .env file.")
if not GEMINI_API_KEY or not GEMINI_API_URL:
    raise ValueError("GEMINI_API_KEY 또는 GEMINI_API_URL이 .env에 설정되어 있지 않습니다.")