from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# 초기화 시 한번만 호출
tokenizer = AutoTokenizer.from_pretrained("google/gemma-3-4b-it")
model = AutoModelForCausalLM.from_pretrained("google/gemma-3-4b-it")
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

def generate_summary(prompt: str) -> str:
    try:
        response = generator(prompt, max_new_tokens=300, do_sample=True, temperature=0.7)
        full_text = response[0]["generated_text"]
        if prompt in full_text:
            return full_text.split(prompt, 1)[-1].strip()
        return full_text.strip()  # fallback
    except Exception as e:
        print(f"[❗️generate_summary 에러] {e}")
        return "추천 응답을 생성하는 데 실패했습니다."