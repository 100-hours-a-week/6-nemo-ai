# src/services/curriculum_writer.py

from models.group import GroupGenerationRequest
from config import GEMINI_API_KEY, GEMINI_API_URL
from httpx import AsyncClient, HTTPStatusError

async def generate_plan(data: GroupGenerationRequest) -> list[str]:
    prompt = f"""
당신은 모임을 소개해주는 AI 비서입니다
다음 모임 정보를 바탕으로 모임 기간에 따라 단계별 커리큘럼을 생성해주세요:

입력 정보:
- 모임명: {data.name}
- 목적: {data.goal}
- 카테고리: {data.category}
- 기간: {data.period}
"""

    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        async with AsyncClient() as client:
            response = await client.post(GEMINI_API_URL, headers=headers, params=params, json=payload)
            response.raise_for_status()
            response_data = await response.json()  # ← 비동기 방식
            generated_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            return generated_text.strip().split('\n')

    except HTTPStatusError as e:
        print(f"[Gemini API 호출 실패] 상태 코드: {e.response.status_code}")
        return []

    except Exception as e:
        print(f"[알 수 없는 예외] {str(e)}")
        return []