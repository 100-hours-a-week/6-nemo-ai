import asyncio
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import httpx
from app.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    success_threshold: int = 2  # Successes needed to close from half-open


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = asyncio.Lock()

    async def is_request_allowed(self) -> bool:
        async with self.lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.OPEN:
                if (time.time() - self.last_failure_time) >= self.config.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    ai_logger.info("[Circuit Breaker] 상태 변경: OPEN -> HALF_OPEN")
                    return True
                return False
            else:  # HALF_OPEN
                return True

    async def record_success(self):
        async with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    ai_logger.info("[Circuit Breaker] 상태 변경: HALF_OPEN -> CLOSED")
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = 0

    async def record_failure(self):
        async with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if (self.state == CircuitBreakerState.CLOSED and 
                self.failure_count >= self.config.failure_threshold):
                self.state = CircuitBreakerState.OPEN
                ai_logger.warning(f"[Circuit Breaker] 상태 변경: CLOSED -> OPEN (failures: {self.failure_count})")
            elif self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                ai_logger.warning("[Circuit Breaker] 상태 변경: HALF_OPEN -> OPEN")


class VLLMHealthMonitor:
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.response_times: List[float] = []
        self.last_health_check = None
        self.is_healthy = True
        self.max_response_time_history = 100  # Keep last 100 response times

    def record_success(self, response_time: float):
        self.success_count += 1
        self.response_times.append(response_time)

        # Keep only recent response times
        if len(self.response_times) > self.max_response_time_history:
            self.response_times.pop(0)

    def record_failure(self):
        self.failure_count += 1

    def get_metrics(self) -> Dict:
        total_requests = self.success_count + self.failure_count
        success_rate = self.success_count / total_requests if total_requests > 0 else 0

        avg_response_time = 0
        p95_response_time = 0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            sorted_times = sorted(self.response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95_response_time = sorted_times[p95_index] if sorted_times else 0

        return {
            "success_rate": success_rate,
            "total_requests": total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_response_time": avg_response_time,
            "p95_response_time": p95_response_time,
            "is_healthy": self.is_healthy,
            "last_health_check": self.last_health_check
        }

    async def health_check(self, vllm_url: str) -> bool:
        """Simple health check to vLLM endpoint"""
        try:
            # Skip health check if URL is not properly configured
            if not vllm_url or vllm_url.strip() == "":
                ai_logger.debug("[Health Check] vLLM URL이 설정되지 않았습니다.")
                self.is_healthy = False
                self.last_health_check = time.time()
                return False

            # Try vLLM specific endpoints that should work
            health_endpoints = [
                f"{vllm_url.rstrip('/')}/v1/models",  # This should work for vLLM
                f"{vllm_url.rstrip('/')}/health",     # Standard health endpoint
                f"{vllm_url.rstrip('/')}/",           # Root endpoint
            ]

            for health_url in health_endpoints:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(health_url)
                        if response.status_code in [200, 404]:  # 404 is also OK, means server is responding
                            self.is_healthy = True
                            self.last_health_check = time.time()
                            ai_logger.debug(f"[Health Check] vLLM 응답 확인됨: {health_url} (status: {response.status_code})")
                            return True
                except httpx.TimeoutException:
                    ai_logger.debug(f"[Health Check] 타임아웃: {health_url}")
                    continue
                except Exception as e:
                    ai_logger.debug(f"[Health Check] 실패: {health_url} - {e}")
                    continue

            # All endpoints failed
            self.is_healthy = False
            self.last_health_check = time.time()
            ai_logger.debug(f"[Health Check] 모든 엔드포인트 실패: {vllm_url}")
            return False

        except Exception as e:
            ai_logger.debug(f"[Health Check] 예외 발생: {e}")
            self.is_healthy = False
            self.last_health_check = time.time()
            return False


class VLLMManager:
    def __init__(self, vllm_url: str, retry_config: RetryConfig = None, 
                 circuit_config: CircuitBreakerConfig = None):
        self.vllm_url = vllm_url.rstrip('/')
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(circuit_config)
        self.health_monitor = VLLMHealthMonitor()

    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute operation with retry logic and circuit breaker"""
        if not await self.circuit_breaker.is_request_allowed():
            ai_logger.warning("[vLLM Manager] 회로 차단기가 OPEN 상태, 요청 거부")
            raise RuntimeError("vLLM 서비스가 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.")

        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                start_time = time.time()
                result = await operation(*args, **kwargs)
                response_time = time.time() - start_time

                await self.circuit_breaker.record_success()
                self.health_monitor.record_success(response_time)

                if attempt > 0:
                    ai_logger.info(f"[vLLM Manager] 재시도 성공 (attempt {attempt + 1})")

                return result

            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout) as e:
                last_exception = e
                await self.circuit_breaker.record_failure()
                self.health_monitor.record_failure()

                if attempt < self.retry_config.max_retries:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
                        self.retry_config.max_delay
                    )
                    ai_logger.warning(
                        f"[vLLM Manager] 요청 실패 (attempt {attempt + 1}), {delay}초 후 재시도: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    ai_logger.error(f"[vLLM Manager] 모든 재시도 실패: {e}")

            except httpx.HTTPStatusError as e:
                await self.circuit_breaker.record_failure()
                self.health_monitor.record_failure()

                if e.response.status_code >= 500 and attempt < self.retry_config.max_retries:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
                        self.retry_config.max_delay
                    )
                    ai_logger.warning(
                        f"[vLLM Manager] 서버 오류 (status: {e.response.status_code}), {delay}초 후 재시도"
                    )
                    await asyncio.sleep(delay)
                    last_exception = e
                else:
                    ai_logger.error(f"[vLLM Manager] HTTP 오류: {e.response.status_code}")
                    raise e

            except Exception as e:
                await self.circuit_breaker.record_failure()
                self.health_monitor.record_failure()
                ai_logger.error(f"[vLLM Manager] 예상치 못한 오류: {e}")
                raise e

        # All retries failed
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("모든 재시도가 실패했습니다.")

    def get_health_metrics(self) -> Dict:
        """Get current health and performance metrics"""
        circuit_state = {
            "state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
            "success_count": self.circuit_breaker.success_count
        }

        health_metrics = self.health_monitor.get_metrics()

        return {
            "circuit_breaker": circuit_state,
            "health": health_metrics,
            "timestamp": time.time()
        }

    async def periodic_health_check(self):
        """Periodic health check that can be run as a background task"""
        while True:
            try:
                await self.health_monitor.health_check(self.vllm_url)
                await asyncio.sleep(300)  # Check every 5 minutes instead of 30 seconds
            except Exception as e:
                ai_logger.error(f"[Health Check] 정기 건강 상태 확인 중 오류: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error
