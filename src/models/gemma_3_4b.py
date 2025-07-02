import httpx, json
from src.core.ai_logger import get_ai_logger
from src.config import vLLM_URL
from src.core.rate_limiter import QueuedExecutor


# model_id = "google/gemma-3-4b-it"
#
# torch.cuda.empty_cache()
# tokenizer = AutoTokenizer.from_pretrained(model_id)
# model = Gemma3ForCausalLM.from_pretrained(model_id).eval()
#
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# model = model.to(device)

queued_executor = QueuedExecutor(max_workers=5, qps=1.5)
ai_logger = get_ai_logger()

async def call_vllm_api(prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
    VLLM_API_URL = vLLM_URL + "v1/completions"
    async def request():
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
                return result.get("choices", [{}])[0].get("text", "").strip()
        except Exception as e:
            raw_text = ""
            try:
                raw_text = (await response.aread()).decode("utf-8", errors="ignore")
            except:
                pass
            raise RuntimeError(f"vLLM 요청 실패: {e}\n원시 응답: {raw_text}")

    try:
        generated = await queued_executor.submit(request)

        if not generated:
            ai_logger.warning("[vLLM] 응답이 비어 있습니다.")
            return "```json\n{\"question\": \"질문 생성 실패\", \"options\": []}\n```"

        ai_logger.info("[vLLM] 응답 수신 성공", extra={
            "length": len(generated),
            "preview": generated[:100]
        })

        return generated

    except Exception as e:
        ai_logger.warning("[vLLM] 응답 실패", extra={
            "error": str(e),
            "prompt": prompt
        })

        return "```json\n{\"question\": \"질문 생성 실패\", \"options\": []}\n```"


async def stream_vllm_response(messages: list[dict]):
    VLLM_API_URL = vLLM_URL + "v1/chat/completions"

    converted_messages = [
        {"role": m["role"], "content": m["text"]} for m in messages
    ]

    payload = {
        "messages": converted_messages,
        "stream": True,
        "max_tokens": 256,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", VLLM_API_URL, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        content = line[len("data:"):].strip()
                        if content == "[DONE]":
                            break
                        try:
                            parsed = json.loads(content)
                            delta = parsed["choices"][0]["delta"]
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except Exception as e:
                            ai_logger.warning(
                                "[vLLM 스트리밍 파싱 실패]",
                                extra={"line": line, "error": str(e)},
                            )
    except httpx.HTTPError as e:
        ai_logger.error("[vLLM SSE 연결 실패]", extra={"error": str(e)})
        raise

async def local_model_generate(prompt: str, max_new_tokens: int = 512) -> str:
    # inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    # input_len = inputs["input_ids"].shape[-1]
    #
    # with torch.no_grad():
    #     outputs = model.generate(
    #         **inputs,
    #         max_new_tokens=max_new_tokens,
    #         do_sample=True,
    #         temperature=0.4,
    #         top_k=50,
    #         top_p=0.8,
    #         repetition_penalty=1.1
    #     )
    #
    # decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # return decoded, input_len
    pass


if __name__ == "__main__":
    import asyncio
    async def test():
        messages = [{"role": "user", "text": "안녕"}]
        async for token in stream_vllm_response(messages):
            print("Token:", token)

    asyncio.run(test())