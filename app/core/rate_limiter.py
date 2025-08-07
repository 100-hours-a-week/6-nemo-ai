import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional
import asyncio
from collections import defaultdict, deque


class RateLimiter:

    def __init__(self, max_requests: int = 100, time_window: int = 3600):
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_log: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()
    
    def is_allowed(self, user_id: str) -> bool:
        if user_id is None:
            return False
            
        if self.max_requests <= 0:
            return False
            
        current_time = time.time()
        
        with self.lock:
            # Clean old requests outside the time window
            user_requests = self.request_log[user_id]
            while user_requests and current_time - user_requests[0] > self.time_window:
                user_requests.popleft()
            
            # Check if under the limit
            if len(user_requests) < self.max_requests:
                user_requests.append(current_time)
                return True
            else:
                return False
    
    def get_remaining_requests(self, user_id: str) -> int:
        """Get the number of remaining requests for a user."""
        if user_id is None:
            return 0
            
        current_time = time.time()
        
        with self.lock:
            user_requests = self.request_log[user_id]
            # Clean old requests
            while user_requests and current_time - user_requests[0] > self.time_window:
                user_requests.popleft()
            
            return max(0, self.max_requests - len(user_requests))
    
    def reset_user_limit(self, user_id: str):
        """Reset rate limit for a specific user."""
        with self.lock:
            if user_id in self.request_log:
                del self.request_log[user_id]


# Global rate limiter instance
_global_rate_limiter = RateLimiter(max_requests=100, time_window=3600)


def is_rate_limited(user_id: str, max_requests: int = 100, time_window: int = 3600) -> bool:
    if max_requests == 100 and time_window == 3600:
        return not _global_rate_limiter.is_allowed(user_id)
    else:
        temp_limiter = RateLimiter(max_requests=max_requests, time_window=time_window)
        return not temp_limiter.is_allowed(user_id)


def get_rate_limit_info(user_id: str) -> Dict[str, int]:
    remaining = _global_rate_limiter.get_remaining_requests(user_id)
    return {
        "max_requests": _global_rate_limiter.max_requests,
        "time_window": _global_rate_limiter.time_window,
        "remaining_requests": remaining,
        "used_requests": _global_rate_limiter.max_requests - remaining
    }


def reset_rate_limit(user_id: str):
    _global_rate_limiter.reset_user_limit(user_id)


class RateLimitedExecutor:
    """동기 작업용 QPS 제한 실행기"""
    def __init__(self, max_workers: int = 5, qps: float = 1.0):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.qps = qps
        self.lock = threading.Lock()
        self.last_run = 0.0

    def _rate_limited_wrapper(self, fn: Callable, *args, **kwargs):
        with self.lock:
            now = time.time()
            wait = max(0, (1 / self.qps) - (now - self.last_run))
            if wait > 0:
                time.sleep(wait)
            self.last_run = time.time()
        return fn(*args, **kwargs)

    def submit(self, fn: Callable, *args, **kwargs):
        return self.executor.submit(self._rate_limited_wrapper, fn, *args, **kwargs)

    def shutdown(self, wait: bool = True):
        self.executor.shutdown(wait=wait)


class QueuedExecutor:
    """비동기 함수 또는 동기 함수를 QPS 및 큐잉 제어와 함께 실행"""
    def __init__(self, max_workers: int = 3, qps: float = 1.0, max_queue_size: int = 100):
        self.semaphore = asyncio.Semaphore(max_workers)
        self.qps = qps
        self.lock = asyncio.Lock()
        self.last_call_time = None
        self.queue = asyncio.Queue(maxsize=max_queue_size)

    async def _respect_qps(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            if self.last_call_time:
                wait_time = max(0, (1 / self.qps) - (now - self.last_call_time))
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            self.last_call_time = asyncio.get_event_loop().time()

    async def submit(self, func: Callable, *args, timeout: float = 30.0, **kwargs):
        try:
            self.queue.put_nowait(1)  # 큐가 가득 차면 예외 발생
        except asyncio.QueueFull:
            raise RuntimeError("요청 큐가 가득 찼습니다. 나중에 다시 시도해주세요.")

        async with self.semaphore:
            await self._respect_qps()
            try:
                if asyncio.iscoroutinefunction(func):
                    coro = func(*args, **kwargs)
                    return await asyncio.wait_for(coro, timeout=timeout)
                else:
                    return await asyncio.wait_for(
                        asyncio.to_thread(func, *args, **kwargs),
                        timeout=timeout,
                    )
            except asyncio.TimeoutError:
                raise RuntimeError(f"요청이 {timeout}초 내에 완료되지 않았습니다.")
            finally:
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except:
                    pass  # Queue might be empty in error cases
    
    def get_queue_status(self) -> dict:
        """Get current queue status for monitoring"""
        return {
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.queue.maxsize,
            "available_workers": self.semaphore._value,
            "qps_limit": self.qps
        }
