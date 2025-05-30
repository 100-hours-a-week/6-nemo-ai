from transformers import AutoModelForCausalLM, AutoTokenizer
from dotenv import load_dotenv
import torch
import os

load_dotenv()
hf_token = os.environ.get("HF_TOKEN")

# 모델 이름 (정확한 Hugging Face repo명 사용)
#model_name = "google/gemma-3-4b-it"
model_name = "kakaocorp/kanana-nano-2.1b-instruct"

# 디바이스 설정: CPU
device = torch.device("cpu")
print(f"Loading model on {device}...")

# 토크나이저 및 모델 로딩
tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
model = AutoModelForCausalLM.from_pretrained(model_name, token=hf_token).to(device)

# 테스트용 프롬프트
prompt = "안녕하세요. 자기소개를 해주세요."
inputs = tokenizer(prompt, return_tensors="pt").to(device)

# 추론
with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=128)

# 결과 출력
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
