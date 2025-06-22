from transformers import AutoTokenizer
from dotenv import load_dotenv
import os

# .env 파일로부터 Hugging Face 토큰과 모델 이름을 불러옴
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = "google/gemma-3-4b-it"

# 토크나이저를 전역 변수로 선언하되 아직 초기화하지 않음
_tokenizer = None     # 토크나이저 싱글톤 객체 (최초 1회만 로딩)

# get_tokenizer 함수는 토크나이저를 lazy-loading 방식으로 반환함
def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        print(f"[토크나이저] '{MODEL_NAME}' 로딩 중...")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
        print(f"[토크나이저] '{MODEL_NAME}' 로드 완료!")
    return _tokenizer



if __name__ == "__main__":
    tokenizer = get_tokenizer()
    print(tokenizer.tokenize("테스트 문장입니다."))

