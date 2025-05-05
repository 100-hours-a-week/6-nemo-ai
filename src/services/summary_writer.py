from src.models.group import GroupGenerationRequest
from src.config import GEMINI_API_KEY, GEMINI_API_URL
from httpx import AsyncClient, HTTPStatusError
from typing import Tuple, List

async def generate_summary(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = f"""
당신은 모임을 소개하는 AI 비서입니다.
다음 모임 정보를 바탕으로 아래 항목을 생성해주세요:

1. 한 줄 소개 (64자 이내)
2. 상세 설명 (500자 이내)

입력 정보:
- 모임명: {data.name}
- 목적: {data.goal}
- 카테고리: {data.category}
- 기간: {data.period}
"""

    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        async with AsyncClient() as client:
            response = await client.post(GEMINI_API_URL, headers=headers, params=params, json=payload)
            response.raise_for_status()
            response_data = await response.json()
            generated_text = response_data["candidates"][0]["content"]["parts"][0]["text"]

            # 예시 출력 포맷:
            # 한 줄 소개
            # 상세 설명
            sections = generated_text.strip().split("\n\n")
            summary = sections[0].strip()
            description = sections[1].strip()

            return summary, description

    except HTTPStatusError as e:
        print(f"[Gemini 요약 실패] 상태 코드: {e.response.status_code}")
        return "요약 실패", "상세 설명 실패"

    except Exception as e:
        print(f"[알 수 없는 예외] {str(e)}")
        return "요약 실패", "상세 설명 실패"