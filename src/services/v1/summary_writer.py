from src.schemas.v1.group_writer import GroupGenerationRequest
from src.config import GEMINI_API_KEY, GEMINI_API_URL
from httpx import AsyncClient, HTTPStatusError
from typing import Tuple
import re
from pprint import pprint

async def generate_summary(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.

    주의 사항:
    - 사용자의 입력에 욕설, 비하, 공격적 표현이 포함된 경우 이를 무시하고 **건전한 텍스트**만 생성해주세요.
    - 욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.
    - 출력에는 절대 이모지(emoji)를 포함하지 마세요.

    다음 모임 정보를 바탕으로 아래 두 항목을 생성해주세요:

    1. 한 줄 소개 (64자 이내): 모임의 성격과 매력을 간결하게 요약한 문장으로 작성하되, 반드시 **명사**로 자연스럽게 마무리해주세요.  
       예시: 실무 중심으로 안드로이드 앱을 개발하는 스터디 모임

    2. 상세 설명 (500자 이내): 어떤 활동을 하는 모임인지, 누가 참여하면 좋은지, 기간 동안 어떤 방식으로 운영되는지 등을 친절하고 명확하게 작성해주세요.

    출력 조건:
    - 실제 줄바꿈(엔터)은 절대 사용하지 마세요.
    - 각 항목의 줄 끝에는 반드시 문자 그대로 **백슬래시 두 개와 소문자 n (`\\n`)**을 넣어주세요.
    - 출력은 다음 형식처럼 **한 줄 문자열**로 이어져야 합니다:

    예시 출력:
    - 한 줄 소개:\\n- 상세 설명:\\n

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
                    description_raw = generated_text.split("- 상세 설명:")[1].strip()

                    # 줄바꿈 문자 제거
                    description_raw = description_raw.replace('\n', '').replace('\\n', '')

                    # 문장 단위 분할 후 각 문장에 \\n 추가 (마침표, 물음표, 느낌표 등 기준)
                    sentences = re.split(r'(?<=[.?!])\s+', description_raw)
                    description = ''.join(s.strip() + '\\n' for s in sentences if s.strip())

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
        pprint(summary)
        print("\n상세 설명:")
        pprint(description)

    asyncio.run(main())
