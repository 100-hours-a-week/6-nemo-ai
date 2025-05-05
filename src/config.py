import os
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)
HF_TOKEN = os.getenv("HF_TOKEN")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

if not HF_TOKEN:
    raise ValueError("No HuggingFace key found. Set it in the .env file.")
if not NGROK_AUTH_TOKEN:
    raise ValueError("No Ngrok Auth Token found. Set it in the .env file.")