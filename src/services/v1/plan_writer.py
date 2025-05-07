from src.schemas.v1.group_writer import GroupGenerationRequest
from src.config import GEMINI_API_KEY, GEMINI_API_URL
from httpx import AsyncClient, HTTPStatusError
from typing import List, Dict

async def generate_plan(data: GroupGenerationRequest) -> str:
    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.
    아래 모임 정보를 바탕으로, 모임의 '목적'을 중심으로 실현 가능한 활동 커리큘럼을 스텝별로 작성해주세요.
    
    
    사용자의 입력이 부적절하거나 욕설이 포함되어 있을 경우,
    이를 무시하고 건전한 택스트만 생성하세요.
    욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.


    조건:
    - 출력에는 절대 이모지(emoji)를 포함하지 마세요.
    - 커리큘럼은 반드시 '모임의 목적'을 기반으로 작성하세요.
    - 전체 기간({data.period}) 동안 실행 가능한 단계 수로 제한해주세요.
    - 일반적으로 1~{data.period} 기간에 따라 1~8단계 이내가 적절합니다. (너무 세부적이지 않게)
    - 각 항목마다 줄 끝에 반드시 '\\n'을 넣어주세요. 이 출력은 프론트엔드에 직접 전달되며 줄바꿈이 필요합니다.
    - 전체 출력은 아래 예시 포맷을 정확히 따라야 합니다.
    - 커리큘럼은 반드시 '모임의 목적'을 중심으로 단계별로 구체적이고 실천 가능한 내용으로 구성되어야 합니다.
    
    - 각 스텝은 다음과 같은 형식을 따라야 합니다:
        - Step: 번호
        - title: 제목 
        - detail: 세부 내용 
        
    출력 예시 (형식을 반드시 지켜주세요):
    - Step: 1\\n
    - title: OT 및 목표 설정\\n
    - detail: 참가자 소개 및 전체 커리큘럼 안내\\n

    - Step: 2\\n
    - title: 기본 개념 이해\\n
    - detail: 목표 달성을 위한 핵심 개념 학습\\n

    ...

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
            response_data = response.json()
            generated_text = response_data["candidates"][0]["content"]["parts"][0]["text"]

            # 여기서 그대로 반환 (긴 문자열 그대로)
            return generated_text.strip()

    except HTTPStatusError as e:
        print(f"[Gemini 커리큘럼 실패] 상태 코드: {e.response.status_code}")
        return []

    except Exception as e:
        print(f"[알 수 없는 예외] {str(e)}")
        return []

if __name__ == "__main__":
    import asyncio
    from src.schemas.v1.group_writer import GroupGenerationRequest

    async def main():
        test_request = GroupGenerationRequest(
            name="딥러닝 실전 스터디",
            goal="딥러닝 기초 이론부터 실습까지 단계적으로 학습",
            category="학습/자기계발",
            period="4주",
            isPlanCreated=True
        )

        plan = await generate_plan(test_request)

        # plan은 이제 긴 문자열이므로 그냥 출력
        print("생성된 커리큘럼:\n")
        print(plan)

    asyncio.run(main())
