from src.models.group import GroupGenerationRequest
from src.config import GEMINI_API_KEY, GEMINI_API_URL
from httpx import AsyncClient, HTTPStatusError
from typing import List, Dict

async def generate_plan(data: GroupGenerationRequest) -> List[Dict[str, str]]:
    prompt = f"""
당신은 모임을 소개하는 AI 비서입니다.
다음 모임 정보를 바탕으로 스텝별 커리큘럼을 구성해주세요.

각 스텝은 다음과 같은 형식을 따라야 합니다:
- Step 번호
- 제목 (title)
- 세부 내용 (detail)

출력 예시는 다음과 같습니다:

- Step: 1
- title: OT 및 목표 설정
- detail: 참가자 소개 및 모임 목표 공유, 전체 일정 안내

- Step: 2
- title: 기본 개념 학습
- detail: 주제에 맞는 핵심 개념 학습

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

            # 파싱 로직 (예시 기준으로)
            lines = generated_text.strip().split("\n\n")
            plan = []

            for line in lines:
                parts = line.strip().split("\n")
                if len(parts) == 3:
                    step_line = parts[0].strip()  # ex: 1단계: OT 및 목표 설정
                    title_line = parts[1].strip().replace("- title: ", "")
                    detail_line = parts[2].strip().replace("- detail: ", "")

                    plan.append({
                        "step": step_line,
                        "title": title_line,
                        "detail": detail_line
                    })

            return plan

    except HTTPStatusError as e:
        print(f"[Gemini 커리큘럼 실패] 상태 코드: {e.response.status_code}")
        return []

    except Exception as e:
        print(f"[알 수 없는 예외] {str(e)}")
        return []
