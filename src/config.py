import os
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

HF_TOKEN = os.getenv("HF_TOKEN")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")
HF_API_URL = os.getenv("HF_API_URL")

if not HF_TOKEN:
    raise ValueError("No HuggingFace token found. Set it in the .env file.")
# if not NGROK_AUTH_TOKEN:
#     raise ValueError("No Ngrok Auth Token found. Set it in the .env file.")
if not GEMINI_API_KEY:
    raise ValueError("No Gemini API Key found. Set it in the .env file.")
if not GEMINI_API_URL:
    raise ValueError("No Gemini endpoint URL found. Set it in the .env file.")
if not HF_API_URL:
    raise ValueError("No HuggingFace API URL found. Set it in the .env file.")