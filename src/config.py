import os
from dotenv import load_dotenv, find_dotenv

# .env 파일 불러오기
env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

# 환경 변수 읽기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")

# 유효성 검사
if not GEMINI_API_KEY or not GEMINI_API_URL:
    raise ValueError("GEMINI_API_KEY 또는 GEMINI_API_URL이 .env에 설정되어 있지 않습니다.")
