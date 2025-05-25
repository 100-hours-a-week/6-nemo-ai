import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import login

# Hugging Face 인증
hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN")
if hf_token:
    login(token=hf_token)

# 모델 이름 (4B GPU 전용)
model_name = "google/gemma-3-4b-it"

# torch_dtype 설정 (GPU: float16 / CPU: float32)
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

# 모델 및 토크나이저 로딩 (device_map 자동 분배)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",             # GPU / CPU 자동 매핑
    torch_dtype=torch_dtype        # 성능 최적화 dtype
)
model.eval()

def build_prompt(data: dict) -> str:
    """
    사용자 입력 기반 프롬프트 생성
    """
    return f"""
당신은 모임을 소개하는 AI 비서입니다.

다음 정보를 바탕으로 모임의 한 줄 소개와 상세 소개를 작성하세요.

모임명: {data['name']}
목적: {data['goal']}
카테고리: {data['category']}
기간: {data['period']}

- 한 줄 소개는 50자 이내로, 마침표 없이 간결하고 자연스럽게 작성하세요.
- 상세 소개는 300자 내외로, 구체적인 설명과 기대 효과를 포함하세요.
- 예의 바르고 친근한 문체를 사용하세요.

출력 예시:
한 줄 소개: ...
상세 소개: ...
    """

def generate_text(data: dict) -> dict:
    """
    프롬프트를 바탕으로 텍스트 생성
    """
    prompt = build_prompt(data)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)

    # device_map 사용 시 입력도 .to(model.device) 불필요 (자동 매핑됨)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            eos_token_id=tokenizer.eos_token_id,
        )

    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    response_text = full_output.replace(prompt.strip(), "").strip()

    # 기본 파싱
    summary, description = "", ""
    lines = [line.strip() for line in response_text.split("\n") if line.strip()]
    for line in lines:
        if "한 줄 소개" in line:
            summary = line.split(":", 1)[-1].strip()
        elif "상세 소개" in line:
            description = line.split(":", 1)[-1].strip()

    return {
        "summary": summary,
        "description": description
    }
