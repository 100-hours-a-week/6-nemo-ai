from transformers import Gemma3ForCausalLM, AutoTokenizer
import torch, httpx
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

# model_id = "google/gemma-3-4b-it"
#
# torch.cuda.empty_cache()
# tokenizer = AutoTokenizer.from_pretrained(model_id)
# model = Gemma3ForCausalLM.from_pretrained(model_id).eval()
#
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# model = model.to(device)

VLLM_API_URL = "http://localhost:8000/generate"

async def generate_explaination(messages: list[dict], group_text: str, debug: bool = False) -> str:
    """
    전체 대화 히스토리 + 추천 그룹 정보를 바탕으로
    이 그룹이 사용자에게 적합한 이유를 자연스럽게 설명합니다.
    """

    # 대화 형식 문자열로 변환 (AI부터 시작해야 함)
    conversation = "\n".join([f"{m['role']}: {m['text']}" for m in messages])

    # 프롬프트 구성
    prompt = f"""
당신은 대화형 추천 챗봇입니다.
다음은 사용자와의 대화 내용입니다. 대화는 'ai'로 시작합니다.

{conversation}

그리고 아래는 추천 후보 모임의 정보입니다:

"{group_text.strip()}"

위 대화를 바탕으로, 이 모임이 사용자의 관심사와 어떻게 잘 맞는지 300자 이내로 공감의 말로 시작하여 설명해 주세요.
너무 일반적이거나 단순한 문장이 아닌, 사용자의 대화 흐름과 연결된 추천 사유여야 합니다.

형식:
- 설명만 출력하세요. "추천드립니다" 등의 마무리 말은 포함해도 괜찮습니다.
- JSON, 마크다운 등 포맷은 포함하지 마세요.
    """.strip()

    try:
        explanation = await call_vllm_api(prompt, max_tokens=300)

        if debug:
            print("📦 생성된 추천 설명:\n", explanation)

        return explanation.strip()

    except Exception as e:
        print(f"[❗️generate_explaination 에러] {e}")
        return "추천 사유를 생성하는 데 실패했습니다."

async def call_vllm_api(prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
    payload = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(VLLM_API_URL, json=payload)

        response.raise_for_status()
        result = response.json()
        generated = result.get("text", "").strip()

        ai_logger.info("[vLLM] 응답 수신 성공", extra={
            "length": len(generated)
        })

        return generated

    except Exception as e:
        ai_logger.warning("[vLLM] 응답 실패", extra={"error": str(e)})
        return "```json\n{\"question\": \"질문 생성 실패\", \"options\": []}\n```"

# async def local_model_generate(prompt: str, max_new_tokens: int = 512) -> str:
#     inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
#     input_len = inputs["input_ids"].shape[-1]
#
#     with torch.no_grad():
#         outputs = model.generate(
#             **inputs,
#             max_new_tokens=max_new_tokens,
#             do_sample=True,
#             temperature=0.4,
#             top_k=50,
#             top_p=0.8,
#             repetition_penalty=1.1
#         )
#
#     decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
#     return decoded, input_len


# if __name__ == "__main__":
#     import asyncio
#     async def run_test():
#         prompt = "딥러닝 동아리에 대한 소개글을 하나의 문장으로 작성해줘."
#         result, _ = await local_model_generate(prompt)
#         print(result)
#     asyncio.run(run_test())