import httpx, json
import asyncio
import time
import re
from src.core.ai_logger import get_ai_logger
from src.config import (
    vLLM_URL,
    VLLM_TIMEOUT,
    VLLM_STREAM_TIMEOUT,
    VLLM_READ_TIMEOUT,
    VLLM_MAX_RETRIES
)
from src.core.rate_limiter import QueuedExecutor
from src.core.vllm_manager import VLLMManager, RetryConfig, CircuitBreakerConfig
from typing import Union, List, AsyncGenerator

# Initialize components
queued_executor = QueuedExecutor(max_workers=5, qps=1.5)
ai_logger = get_ai_logger()

# Initialize vLLM Manager with configurations
retry_config = RetryConfig(
    max_retries=VLLM_MAX_RETRIES,
    base_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0
)

circuit_config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0,
    success_threshold=2
)

vllm_manager = VLLMManager(vLLM_URL, retry_config, circuit_config)

# Start health monitoring as background task
_health_check_task = None


async def start_health_monitoring():
    """Start the health monitoring background task"""
    global _health_check_task
    if _health_check_task is None or _health_check_task.done():
        _health_check_task = asyncio.create_task(vllm_manager.periodic_health_check())
        ai_logger.info("[vLLM Manager] 건강 상태 모니터링 시작")


async def get_vllm_health_metrics():
    """Get current vLLM health metrics including queue status"""
    base_metrics = vllm_manager.get_health_metrics()
    queue_status = queued_executor.get_queue_status()
    
    return {
        **base_metrics,
        "queue_status": queue_status
    }





async def call_vllm_api(prompt: Union[str, List[str]], max_tokens: int = 512, temperature: float = 0.7) -> Union[
    str, List[str]]:
    """Enhanced vLLM API call with retry logic and circuit breaker"""
    VLLM_API_URL = f"{vLLM_URL.rstrip('/')}/v1/completions"

    async def make_request():
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        timeout_config = httpx.Timeout(
            connect=10.0,
            read=VLLM_READ_TIMEOUT,
            write=10.0,
            pool=VLLM_TIMEOUT
        )

        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(VLLM_API_URL, json=payload)
            response.raise_for_status()
            result = response.json()

            if isinstance(prompt, list):
                generated_texts = [c.get("text", "").strip() for c in result.get("choices", [])]
                return generated_texts
            else:
                generated_text = result.get("choices", [{}])[0].get("text", "").strip()
                return generated_text

    try:
        # Start health monitoring if not already running
        await start_health_monitoring()

        # Execute request through rate limiter and retry mechanism
        generated = await queued_executor.submit(
            vllm_manager.execute_with_retry,
            make_request,
            timeout=VLLM_TIMEOUT + 10.0  # Add buffer for retries
        )

        # Check for empty response and retry if needed
        retry_count = 0
        max_empty_retries = 2
        
        while (not generated or (isinstance(generated, str) and generated.strip() == "")) and retry_count < max_empty_retries:
            ai_logger.warning(f"[vLLM] 응답이 비어 있습니다. 재시도 {retry_count + 1}/{max_empty_retries}")
            retry_count += 1
            await asyncio.sleep(1.0)  # Wait before retry
            
            try:
                generated = await queued_executor.submit(
                    vllm_manager.execute_with_retry,
                    make_request,
                    timeout=VLLM_TIMEOUT + 10.0
                )
            except Exception as e:
                ai_logger.warning(f"[vLLM] 재시도 중 오류: {e}")
                break

        if not generated or (isinstance(generated, str) and generated.strip() == ""):
            ai_logger.warning("[vLLM] 모든 재시도 후에도 응답이 비어 있습니다.")
            return await _get_fallback_response(prompt)

        if isinstance(generated, list):
            ai_logger.info("[vLLM] 배치 응답 수신 성공", extra={"count": len(generated)})
        else:
            ai_logger.info("[vLLM] 응답 수신 성공", extra={
                "length": len(generated),
                "preview": generated[:100]
            })

        return generated

    except Exception as e:
        ai_logger.error("[vLLM] 응답 실패", extra={
            "error": str(e),
            "prompt_preview": str(prompt)[:100] if prompt else "None",
            "is_recommendation_prompt": "설명을 작성하세요" in str(prompt) if isinstance(prompt, str) else False
        })
        return await _get_fallback_response(prompt)


async def stream_vllm_response(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Enhanced streaming vLLM response with timeout and monitoring"""
    VLLM_API_URL = f"{vLLM_URL.rstrip('/')}/v1/chat/completions"

    converted_messages = [
        {"role": m["role"], "content": m["text"]} for m in messages
    ]

    payload = {
        "messages": converted_messages,
        "stream": True,
        "max_tokens": 256,
        "temperature": 0.7,
    }

    async def stream_request():
        timeout_config = httpx.Timeout(
            connect=10.0,
            read=VLLM_READ_TIMEOUT,
            write=10.0,
            pool=None  # No pool timeout for streaming
        )

        async with httpx.AsyncClient(timeout=timeout_config) as client:
            async with client.stream("POST", VLLM_API_URL, json=payload) as response:
                response.raise_for_status()

                start_time = time.time()
                token_count = 0
                last_token_time = start_time

                async for line in response.aiter_lines():
                    current_time = time.time()

                    # Check for overall stream timeout
                    if current_time - start_time > VLLM_STREAM_TIMEOUT:
                        ai_logger.warning(
                            f"[vLLM 스트리밍] 전체 타임아웃 초과 ({VLLM_STREAM_TIMEOUT}초)"
                        )
                        break

                    # Check for token timeout (no new tokens for 30 seconds)
                    if current_time - last_token_time > 30:
                        ai_logger.warning("[vLLM 스트리밍] 토큰 수신 타임아웃 (30초 무응답)")
                        break

                    if line.startswith("data:"):
                        content = line[len("data:"):].strip()
                        if content == "[DONE]":
                            break

                        try:
                            parsed = json.loads(content)
                            delta = parsed["choices"][0]["delta"]
                            token = delta.get("content", "")
                            if token:
                                token_count += 1
                                last_token_time = current_time
                                yield token
                        except Exception as e:
                            ai_logger.warning(
                                "[vLLM 스트리밍 파싱 실패]",
                                extra={"line": line[:100], "error": str(e)},
                            )

                ai_logger.info(f"[vLLM 스트리밍] 완료 - 토큰 수: {token_count}, 소요 시간: {current_time - start_time:.2f}초")

    # Check circuit breaker before starting stream
    if not await vllm_manager.circuit_breaker.is_request_allowed():
        ai_logger.warning("[vLLM 스트리밍] Circuit breaker is OPEN, using fallback")
        fallback_text = "죄송합니다. 일시적인 오류로 응답을 생성할 수 없습니다."
        for char in fallback_text:
            yield char
            await asyncio.sleep(0.05)
        return

    try:
        # Start health monitoring if not already running
        await start_health_monitoring()

        # Execute streaming request with basic retry for connection errors
        retry_count = 0
        max_retries = 2
        
        while retry_count <= max_retries:
            try:
                start_time = time.time()
                token_yielded = False
                
                async for token in stream_request():
                    token_yielded = True
                    yield token
                
                # If we got here, the stream completed successfully
                await vllm_manager.circuit_breaker.record_success()
                response_time = time.time() - start_time
                vllm_manager.health_monitor.record_success(response_time)
                break
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                await vllm_manager.circuit_breaker.record_failure()
                vllm_manager.health_monitor.record_failure()
                
                if retry_count < max_retries and not token_yielded:
                    retry_count += 1
                    delay = 2 ** (retry_count - 1)  # 1s, 2s delays
                    ai_logger.warning(f"[vLLM 스트리밍] 재시도 {retry_count}/{max_retries} - {delay}초 후 재시도: {e}")
                    await asyncio.sleep(delay)
                else:
                    raise e

    except Exception as e:
        ai_logger.error("[vLLM 스트리밍] 요청 실패", extra={"error": str(e)})
        await vllm_manager.circuit_breaker.record_failure()
        vllm_manager.health_monitor.record_failure()

        # Yield fallback stream content
        fallback_text = "죄송합니다. 일시적인 오류로 응답을 생성할 수 없습니다."
        for char in fallback_text:
            yield char
            await asyncio.sleep(0.05)  # Simulate streaming


async def _get_fallback_response(prompt: Union[str, List[str]]) -> Union[str, List[str]]:
    """Generate fallback response when vLLM fails"""
    # Check if this is a question generation prompt or recommendation explanation prompt
    if isinstance(prompt, str):
        prompt_lower = prompt.lower()
        # Check for question generation indicators
        if ("JSON으로만 출력하세요" in prompt or 
            "question" in prompt_lower or 
            "options" in prompt_lower or
            "선택지" in prompt):
            # This is likely a question generation request
            fallback_text = '{"question": "모임에 참여할 때 어떤 점을 가장 중요하게 생각하시나요?", "options": ["분위기", "활동 내용", "참여자", "일정"]}'
            ai_logger.info("[vLLM Fallback] 질문 생성 fallback 사용")
        elif ("설명을 작성하세요" in prompt or 
              "추천" in prompt or 
              "이유" in prompt or
              "적합한" in prompt):
            # This is likely a recommendation explanation request
            fallback_text = "이 모임은 당신의 대화 내용과 잘 어울리는 것 같아서 추천드려요. 새로운 사람들과 함께 즐거운 시간을 보내실 수 있을 거예요!"
            ai_logger.info("[vLLM Fallback] 추천 설명 fallback 사용")
        else:
            # Default to recommendation explanation
            fallback_text = "이 모임은 당신의 관심사와 잘 맞는 것 같아요. 참여해보시면 좋은 경험이 될 것 같습니다!"
            ai_logger.info("[vLLM Fallback] 기본 추천 설명 fallback 사용")
    else:
        # For list prompts, default to question format
        fallback_text = '{"question": "모임에 참여할 때 어떤 점을 가장 중요하게 생각하시나요?", "options": ["분위기", "활동 내용", "참여자", "일정"]}'
        ai_logger.info("[vLLM Fallback] 배치 질문 생성 fallback 사용")

    if isinstance(prompt, list):
        return [fallback_text for _ in prompt]
    else:
        return fallback_text

async def local_model_generate(prompt: str, max_new_tokens: int = 512) -> str:
    """Placeholder for local model generation (currently disabled)"""
    # Local model code commented out as in original
    pass


if __name__ == "__main__":
    import asyncio

    async def test_streaming():
        messages = [{"role": "user", "text": "안녕하세요"}]
        async for token in stream_vllm_response(messages):
            ai_logger.info(f"Token: {token}")


    async def test_health_metrics():
        await start_health_monitoring()
        await asyncio.sleep(2)  # Let health check run
        metrics = await get_vllm_health_metrics()
        ai_logger.info(f"Health Metrics: {json.dumps(metrics, indent=2)}")


    async def main():
        ai_logger.info("Testing streaming...")
        await test_streaming()
        ai_logger.info("Testing health metrics...")
        await test_health_metrics()


    asyncio.run(main())
