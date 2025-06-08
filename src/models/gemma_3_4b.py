from transformers import AutoTokenizer, AutoModelForCausalLM, AutoProcessor
import torch

model_id = "google/gemma-3-4b-it"

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id).eval()
processor = AutoProcessor.from_pretrained(model_id)

def generate_summary(user_query: str, group_texts: list[str]) -> str:
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
            return_tensors="pt"
        ).to(model.device)

        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=300,
                do_sample=True,
                temperature=0.7
            )

        decoded = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        return decoded.strip()
    except Exception as e:
        print(f"[❗️generate_summary 에러] {e}")
        return "추천 응답을 생성하는 데 실패했습니다."