import os
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("No HuggingFace key found. Set it in the .env file.")