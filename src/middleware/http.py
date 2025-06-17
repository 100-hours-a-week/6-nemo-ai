from fastapi import Request

async def log_requests(request: Request, call_next):
    print(f"📥 Incoming {request.method} request to {request.url.path}")
    print("🔸 Headers:", dict(request.headers))

    body = await request.body()
    print("🔹 Body:", body.decode('utf-8', errors='ignore'))

    response = await call_next(request)
    return response
