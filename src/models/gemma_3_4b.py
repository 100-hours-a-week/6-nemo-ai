from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# 초기화 시 한번만 호출
tokenizer = AutoTokenizer.from_pretrained("google/gemma-3-4b-it")
model = AutoModelForCausalLM.from_pretrained("google/gemma-3-4b-it")
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

def generate_summary(prompt: str) -> str:
    response = generator(prompt, max_new_tokens=256, do_sample=True, temperature=0.7)
    return response[0]["generated_text"].strip()