from app.schemas.groups.group_information import MeetingInput, MeetingData
from app.schemas.groups.group_writer import GroupGenerationRequest
from app.services.v2.tag_extraction import extract_tags
from app.services.v2.description_writer import generate_description
from app.services.v2.plan_writer import generate_plan
from app.services.shared.retry_handler import RetryHandler, ContentValidator
from app.core.ai_logger import get_ai_logger
import asyncio
from typing import Tuple, List

ai_logger = get_ai_logger()

async def build_meeting_data(input: MeetingInput) -> MeetingData:
    """Enhanced V2 build_meeting_data with retry logic and content filtering"""
    
    ai_logger.info("[AI-V2-ENHANCED] [모임 정보 생성 시작]", extra={
        "meeting_name": input.name,
        "has_plan": input.isPlanCreated
    })
    
    group_data = GroupGenerationRequest(
        name=input.name,
        goal=input.goal,
        category=input.category,
        period=input.period,
        isPlanCreated=input.isPlanCreated,
    )
    
    retry_handler = RetryHandler(max_retries=3, base_delay=1.0)
    topic_context = f"{input.name} {input.goal} {input.category}"
    
    # Define validation function for meeting data
    def validate_result(result: MeetingData) -> Tuple[bool, List[str]]:
        return ContentValidator.validate_meeting_data(
            result.name,
            result.summary,  
            result.description,
            result.tags,
            topic_context
        )
    
    # Define the main generation operation
    async def generate_meeting_data() -> MeetingData:
        try:
            # Generate description and plan concurrently with retry
            description_task = retry_handler.retry_with_validation(
                generate_description,
                lambda result: (
                    not ContentValidator.is_empty_or_invalid(result[0]) and 
                    not ContentValidator.is_empty_or_invalid(result[1]) and
                    not ContentValidator.contains_pii(result[0]) and
                    not ContentValidator.contains_pii(result[1]) and
                    not ContentValidator.contains_irrelevant_content(result[0], topic_context) and
                    not ContentValidator.contains_irrelevant_content(result[1], topic_context),
                    ["Invalid or problematic summary/description"] if not (
                        not ContentValidator.is_empty_or_invalid(result[0]) and 
                        not ContentValidator.is_empty_or_invalid(result[1]) and
                        not ContentValidator.contains_pii(result[0]) and
                        not ContentValidator.contains_pii(result[1]) and
                        not ContentValidator.contains_irrelevant_content(result[0], topic_context) and
                        not ContentValidator.contains_irrelevant_content(result[1], topic_context)
                    ) else []
                ),
                "description_generation",
                group_data
            )
            
            plan_task = None
            if input.isPlanCreated:
                plan_task = retry_handler.retry_with_validation(
                    generate_plan,
                    lambda result: (
                        not ContentValidator.is_empty_or_invalid(result) and
                        not ContentValidator.contains_pii(result) and
                        not ContentValidator.contains_irrelevant_content(result, topic_context),
                        ["Invalid or problematic plan"] if (
                            ContentValidator.is_empty_or_invalid(result) or
                            ContentValidator.contains_pii(result) or
                            ContentValidator.contains_irrelevant_content(result, topic_context)
                        ) else []
                    ),
                    "plan_generation",
                    group_data
                )
            
            # Wait for description generation
            summary, description = await description_task
            
            # Clean the content immediately
            summary = ContentValidator.clean_content(summary, topic_context)
            description = ContentValidator.clean_content(description, topic_context)
            
            # Generate tags with retry
            tags = await retry_handler.retry_with_validation(
                extract_tags,
                lambda result: (len(result) > 0, ["No tags generated"] if len(result) == 0 else []),
                "tag_extraction", 
                description
            )
            
            # Filter tags to remove any PII or irrelevant content
            filtered_tags = []
            for tag in tags:
                if (not ContentValidator.contains_pii(tag) and 
                    not ContentValidator.contains_irrelevant_content(tag, topic_context) and
                    not ContentValidator.is_empty_or_invalid(tag)):
                    cleaned_tag = ContentValidator.clean_content(tag, topic_context)
                    if cleaned_tag and cleaned_tag not in filtered_tags:
                        filtered_tags.append(cleaned_tag)
            
            # Wait for plan generation if needed
            plan = None
            if plan_task:
                plan = await plan_task
                if plan:
                    plan = ContentValidator.clean_content(plan, topic_context)
            
            return MeetingData(
                name=input.name,
                summary=summary,
                description=description,
                tags=filtered_tags,
                plan=plan,
            )
            
        except Exception as e:
            ai_logger.exception("[AI-V2-ENHANCED] [컴포넌트 생성 실패]")
            raise e
    
    try:
        # Generate with overall validation and retry
        result = await retry_handler.retry_with_validation(
            generate_meeting_data,
            validate_result,
            "complete_meeting_data_generation"
        )
        
        ai_logger.info("[AI-V2-ENHANCED] [모임 정보 생성 완료]", extra={
            "tags_count": len(result.tags),
            "has_plan": result.plan is not None,
            "summary_length": len(result.summary),
            "description_length": len(result.description)
        })
        
        return result
        
    except Exception as e:
        ai_logger.exception("[AI-V2-ENHANCED] [모임 정보 생성 최종 실패]")
        
        # Return comprehensive fallback data instead of empty fields
        fallback_summary = f"{input.category} 분야의 {input.name}"
        if "모임" not in fallback_summary and "스터디" not in fallback_summary:
            fallback_summary += " 모임"
            
        fallback_description = f"이 모임은 {input.goal}을 목적으로 {input.period} 동안 진행됩니다."
        
        # Add category-specific content to description
        if "스터디" in input.category or "학습" in input.category:
            fallback_description += " 함께 학습하며 목표를 달성하고 성장할 수 있는 기회를 제공합니다."
        elif "운동" in input.category or "건강" in input.category:
            fallback_description += " 건강한 활동을 통해 체력 향상과 친목을 도모할 수 있습니다."
        elif "취미" in input.category:
            fallback_description += " 공통 관심사를 바탕으로 즐거운 시간을 보내며 새로운 경험을 쌓을 수 있습니다."
        elif "친목" in input.category or "사교" in input.category:
            fallback_description += " 새로운 사람들과 만나 소통하며 즐거운 시간을 보낼 수 있습니다."
        else:
            fallback_description += " 관심있는 분들과 함께 유익한 시간을 보낼 수 있는 모임입니다."
        
        fallback_description += " 적극적인 참여를 환영합니다."
        
        # Generate proper fallback tags
        fallback_tags = []
        if input.category:
            fallback_tags.append(input.category)
        fallback_tags.extend(["모임", "활동"])
        
        # Generate proper fallback plan if needed
        fallback_plan = None
        if input.isPlanCreated:
            fallback_plan = f"Step 1: 모임 시작 및 목표 설정\n - {input.goal}에 대한 구체적인 계획을 세웁니다.\n - 참여자들과 목표를 공유하고 진행 방식을 정합니다.\n\nStep 2: 활동 진행\n - 계획된 활동을 차례대로 진행합니다.\n - 참여자들과 적극적으로 소통하며 진행합니다.\n\nStep 3: 마무리 및 평가\n - 활동에 대해 함께 평가하고 피드백을 나눕니다."
        
        return MeetingData(
            name=input.name,
            summary=fallback_summary,
            description=fallback_description,
            tags=fallback_tags,
            plan=fallback_plan,
        )

if __name__ == "__main__":
    test_input = MeetingInput(
        name="토익 스터디 모임",
        goal="함께 공부해서 다음 달 토익 시험 목표 점수 달성하기",
        category="학습/자기계발",
        period="1개월 이하",
        isPlanCreated=True,
    )

    async def run_test():
        result = await build_meeting_data(test_input)
        print(result)

    asyncio.run(run_test())
