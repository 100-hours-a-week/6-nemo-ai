from src.schemas.v1.group_writer import GroupGenerationRequest
from src.config import GEMINI_API_KEY, GEMINI_API_URL
from httpx import AsyncClient, HTTPStatusError
from typing import Tuple


async def generate_summary(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.
    
    사용자의 입력이 부적절하거나 욕설이 포함되어 있을 경우,
    이를 무시하고 건전한 택스트만 생성하세요.
    욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.
    
    다음 모임 정보를 바탕으로 아래 두 항목을 생성해주세요:

    1. 한 줄 소개 (64자 이내): 모임의 성격과 매력을 간결하게 요약한 문장으로 작성하되, 반드시 **명사**로 자연스럽게 마무리해주세요.
    예시: 실무 중심으로 안드로이드 앱을 개발하는 스터디 모임

    2. 상세 설명 (500자 이내): 어떤 활동을 하는 모임인지, 누가 참여하면 좋은지, 기간 동안 어떤 방식으로 운영되는지 등을 친절하고 명확하게 작성해주세요.


    출력 형식:
    - 한 줄 소개:\\n
    - 상세 설명:\\n

    출력의 각 항목 끝에는 반드시 '\\n'을 포함해주세요. 이 출력은 프론트엔드에서 줄바꿈 처리를 위해 직접 사용됩니다.
    **출력에는 이모지(emoji)를 절대 포함하지 마세요.**

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
        print("한 줄 소개:")
        print(summary)
        print("\n상세 설명:")
        print(description)

    asyncio.run(main())
