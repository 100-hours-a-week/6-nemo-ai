from src.schemas.v1.group_writer import GroupGenerationRequest, GroupGenerationResponse
from src.services.v1.summary_writer import generate_summary

async def generate_group_info(data: GroupGenerationRequest) -> GroupGenerationResponse:
    summary, description = await generate_summary(data)

    return GroupGenerationResponse(
        summary=summary,
        description=description,
    )

if __name__ == "__main__":
    import asyncio
    async def main():
        # 테스트용 입력값 구성
        test_request = GroupGenerationRequest(
            name="AI 스터디 모임",
            goal="딥러닝 논문 읽고 토론하기",
            category="학습/자기계발",
            period="6주",
            isPlanCreated=True
        )

        # 비동기 함수 실행
        result = await generate_group_info(test_request)

        # 결과 출력
        print("요약:", result.summary)
        print("상세 설명:", result.description)

    asyncio.run(main())