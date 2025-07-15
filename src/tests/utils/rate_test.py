from fastapi import APIRouter
import asyncio
from datetime import datetime
from src.core.rate_limiter import QueuedExecutor  # 경로는 사용자의 구조에 맞게 조정

router = APIRouter()

executor = QueuedExecutor(max_workers=2, qps=1.0, max_queue_size=5)

def now_str():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

@router.get("/test/limited")
async def limited_task(n: int):
    async def task():
        print(f"[{now_str()}] ✅ 작업 {n} 시작")
        await asyncio.sleep(0.5)  # 실제 처리 시간
        print(f"[{now_str()}] 🏁 작업 {n} 완료")
        return {"status": "ok", "task": n}

    try:
        result = await executor.submit(task, timeout=3.0)
        return result
    except Exception as e:
        print(f"[{now_str()}] ❌ 작업 {n} 실패: {e}")
        return {"status": "failed", "task": n, "error": str(e)}
