from transformers import Gemma3ForConditionalGeneration, AutoTokenizer, AutoProcessor
import torch
import json

model_id = "google/gemma-3-4b-it"

processor = AutoProcessor.from_pretrained(model_id)
model = Gemma3ForConditionalGeneration.from_pretrained(model_id).eval()

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

        inputs = processor.apply_chat_template(
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

        decoded = processor.decode(outputs[0][input_len:], skip_special_tokens=True)

        if debug:
            print(f"📏 Input Tokens: {input_len}, Output Tokens: {outputs.shape}")
            print(f"📦 생성된 텍스트:\n{decoded}")
            if torch.cuda.is_available():
                print(f"🧠 GPU 메모리 사용량: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")

        return decoded.strip()

    except Exception as e:
        print(f"[❗️generate_summary 에러] {e}")
        return "추천 응답을 생성하는 데 실패했습니다."

def generate_mcq_questions(max_tokens=500, temp=0.7, debug: bool = False) -> list[dict]:
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
                            "- 질문은 모두 '모임' 또는 '사용자 성향'에 관련되어야 합니다.\n"
                            "- 각 질문은 3~5개의 보기를 포함해야 합니다.\n"
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

        inputs = processor.apply_chat_template(
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

        decoded = processor.decode(outputs[0][input_len:], skip_special_tokens=True)

        if debug:
            print(f"📦 생성된 MCQ 질문:\n{decoded}")

        try:
            return json.loads(decoded.strip())
        except Exception as parse_err:
            print(f"[❗️JSON 파싱 실패] {parse_err}")
            print(f"[🔍 원본 출력]: {decoded}")
            return []

    except Exception as e:
        print(f"[❗️generate_mcq_questions 에러] {e}")
        return []
