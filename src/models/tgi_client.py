import os
import time
import httpx
from typing import Tuple
from src.core.tokenizer import get_tokenizer
from src.core.ai_logger import get_ai_logger

logger = get_ai_logger()

TGI_SERVER_URL = os.getenv("TGI_SERVER_URL", "http://localhost:8080/generate")

async def tgi_generate(prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> Tuple[str, int]:
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "do_sample": True,
            "return_full_text": False
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            start_time = time.time()
            response = await client.post(TGI_SERVER_URL, json=payload)
            response.raise_for_status()
            latency = round((time.time() -start_time) * 1000)  # ms 단위
            data = response.json()

            # TGI 출력 구조는 리스트 형태일 수 있음
            # 최신 버전 기준으로는 `data[0]['generated_text']`
            if isinstance(data, list) and "generated_text" in data[0]:
                output_text = data[0]["generated_text"]
            elif "generated_text" in data:
                output_text = data["generated_text"]
            else:
                raise ValueError("TGI 응답에 'generated_text' 없음")

            input_len = len(prompt.strip().split())  # 입력 길이 추정
            logger.info(f"[TGI 성공] 입력 토큰 수: {input_len} | 응답 시간: {latency}ms")

            return output_text, input_len

        except Exception as e:
            logger.error(f"[TGI 에러] {e}")
            raise


