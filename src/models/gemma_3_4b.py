from transformers import Gemma3ForCausalLM, AutoTokenizer
import torch, json, re

model_id = "google/gemma-3-4b-it"

torch.cuda.empty_cache()
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = Gemma3ForCausalLM.from_pretrained(model_id).eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)


def generate_explaination(user_query: str, group_texts: list[str], max_tokens=500, temp=0.7, debug: bool = False) -> str:
    try:
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "당신은 친절한 추천 어시스턴트입니다."}]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"사용자의 요청: \"{user_query}\"\n\n"
                            f"아래는 추천할 수 있는 모임 리스트입니다:\n\n"
                            + "\n\n".join(f"- {t}" for t in group_texts)
                            + "\n\n각 모임이 사용자의 요청과 어떤 점에서 잘 맞는지 300자 이내로 설명해 주세요. 각 설명은 이유 중심이며 공감의 말로 시작해야 합니다."
                        )
                    }
                ]
            }
        ]

        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt"
        ).to(device)

        input_len = inputs["input_ids"].shape[-1]

        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=temp
            )

        decoded = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)

        if debug:
            print(f"📏 Input Tokens: {input_len}, Output Tokens: {outputs.shape}")
            print(f"📦 생성된 텍스트:\n{decoded}")
            if torch.cuda.is_available():
                print(f"🧠 GPU 메모리 사용량: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")

        return decoded.strip()

    except Exception as e:
        print(f"[❗️generate_explaination 에러] {e}")
        return "추천 응답을 생성하는 데 실패했습니다."


def generate_mcq_questions(max_tokens=500, temp=0.7, debug: bool = False, use_context: bool = True) -> list[dict]:
    if use_context:
        return [
            {
                "question": "당신은 어떤 분위기의 모임을 선호하시나요?",
                "options": ["조용한", "활기찬", "편안한", "새로운 사람들과 어울릴 수 있는"]
            },
            {
                "question": "하루 중 모임에 참여하고 싶은 시간대는 언제인가요?",
                "options": ["오전", "오후", "저녁", "시간 상관없음"]
            },
            {
                "question": "어떤 활동에 가장 흥미를 느끼시나요?",
                "options": ["운동", "스터디", "문화 체험", "수다 나누기"]
            }
        ]

    try:
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "당신은 친절한 추천 어시스턴트입니다."}]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "사용자의 성향과 모임 선호도를 파악하기 위해 아래 조건을 만족하는 객관식 질문 3개를 생성해 주세요:\n"
                            "- 질문은 모두 '모임' 또는 '사용자 성향'에 관련되어야 합니다. 질문은 100자 이내로 작성해주세요\n"
                            "- 각 질문은 3~5개의 보기를 포함해야 합니다. 보기는 20자 이내로 작성해주세요.\n"
                            "- JSON 포맷으로 출력해 주세요.\n"
                            "[\n"
                            "  {\n"
                            "    \"question\": \"...\",\n"
                            "    \"options\": [\"선택지1\", \"선택지2\", ...]\n"
                            "  }\n"
                            "]"
                        )
                    }
                ]
            }
        ]

        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt"
        ).to(device)

        input_len = inputs["input_ids"].shape[-1]

        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                top_k=40
            )

        decoded = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
        cleaned = re.sub(r"```json|```", "", decoded.strip()).strip()

        if debug:
            print(f"📦 생성된 MCQ 질문:\n{cleaned}")

        return json.loads(cleaned)
    except Exception as e:
        print(f"[❗️generate_mcq_questions 에러] {e}")
        return []

async def local_model_generate(prompt: str, max_new_tokens: int = 512) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[-1]

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
        result, _ = await local_model_generate(prompt)
        print(result)
    asyncio.run(run_test())