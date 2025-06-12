from transformers import Gemma3ForCausalLM, AutoTokenizer
from dotenv import load_dotenv
import torch
import os

# 환경 변수에서 Hugging Face 토큰 읽기
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

# 로컬 모델 이름
MODEL_NAME = "google/gemma-3-4b-it"

# 모델/토크나이저 로딩
print(f"[로컬모델] '{MODEL_NAME}' 로딩 중...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)

model = Gemma3ForCausalLM.from_pretrained(
    MODEL_NAME,
    token=HF_TOKEN,
    device_map="auto"            # 자동으로 GPU 로드
).eval()

# 디바이스 설정 (CPU 우선, GPU 준비되면 cuda로 교체)
#device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#model = model.to(device)
print(f"[로컬모델] '{MODEL_NAME}' 로드 완료!")

# 공통 모델 호출 함수
async def local_model_generate(prompt: str, max_new_tokens: int = 512) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[-1] #슬라이싱을 위한 입력 길이 추출

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.4,
            top_k=50,
            top_p=0.8,
            repetition_penalty=1.1
        )

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return decoded, input_len


if __name__ == "__main__":
    import asyncio
    async def run_test():
        prompt = "딥러닝 동아리에 대한 소개글을 하나의 문장으로 작성해줘."
        result = await local_model_generate(prompt)
        print(result)
    asyncio.run(run_test())
