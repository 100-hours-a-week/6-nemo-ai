import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
import asyncio

class RateLimitedExecutor:
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
    def __init__(self, max_workers: int = 3, qps: float = 1.0):
        self.semaphore = asyncio.Semaphore(max_workers)
        self.qps = qps
        self.lock = asyncio.Lock()
        self.last_call_time = None

    async def submit(self, func: Callable, *args, **kwargs):
        async with self.semaphore:
            await self._respect_qps()
            return await asyncio.to_thread(func, *args, **kwargs)

    async def _respect_qps(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            if self.last_call_time:
                wait_time = max(0, (1 / self.qps) - (now - self.last_call_time))
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            self.last_call_time = asyncio.get_event_loop().time()