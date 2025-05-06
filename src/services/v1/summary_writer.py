from src.schemas.v1.group_writer import GroupGenerationRequest
from src.config import GEMINI_API_KEY, GEMINI_API_URL
from httpx import AsyncClient, HTTPStatusError
from typing import Tuple


async def generate_summary(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.
    아래 모임 정보를 바탕으로 다음 두 항목을 생성해주세요:

    1. 한 줄 소개 (64자 이내) — 모임의 성격과 매력을 간결하게 요약한 문장
    2. 상세 설명 (500자 이내) — 어떤 활동을 할 모임인지, 누가 참여하면 좋은지, 기간 동안 어떤 방식으로 진행되는지를 친절하고 명확하게 설명

    출력 형식:
    - 한 줄 소개:\\n
    - 상세 설명:\\n

    각 항목의 줄 끝에는 반드시 '\\n'을 포함해주세요. 이 출력은 프론트엔드에 직접 전달되며 줄바꿈 처리를 위해 필요합니다.
    출력에는 절대 이모지(emoji)를 포함하지 마세요.

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

            summary = "요약 파싱 실패"
            description = "상세 설명 파싱 실패"

            if "- 한 줄 소개:" in generated_text and "- 상세 설명:" in generated_text:
                try:
                    summary = generated_text.split("- 한 줄 소개:")[1].split("- 상세 설명:")[0].strip()
                    description = generated_text.split("- 상세 설명:")[1].strip()
                except Exception as e:
                    print(f"[파싱 예외] {str(e)}")
            else:
                print("[포맷 불일치] '한 줄 소개' 또는 '상세 설명' 라벨이 누락됨")

            return summary, description

    except HTTPStatusError as e:
        print(f"[Gemini 요약 실패] 상태 코드: {e.response.status_code}")
        return "요약 실패", "상세 설명 실패"

    except Exception as e:
        print(f"[알 수 없는 예외] {str(e)}")
        return "요약 실패", "상세 설명 실패"

if __name__ == "__main__":
    import asyncio
    from src.schemas.v1.group_writer import GroupGenerationRequest

    async def main():
        # 테스트용 데이터 정의
        test_request = GroupGenerationRequest(
            name="AI 초보 스터디",
            goal="딥러닝 기초 개념을 학습하고 실습 중심으로 진행",
            category="학습/자기계발",
            period="4주",
            isPlanCreated=False  # 이 필드는 generate_summary에 영향을 주지 않음
        )

        # 요약 생성 호출
        summary, description = await generate_summary(test_request)

        # 결과 출력
        print("✅ 한 줄 소개:")
        print(summary)
        print("\n📝 상세 설명:")
        print(description)

    asyncio.run(main())
