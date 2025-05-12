from typing import Tuple
from src.schemas.v1.group_writer import GroupGenerationRequest
from src.core.vertex_client import gen_model, config_model
# from src.core.cloud_logging import logger
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.

    주의 사항:
    - 사용자의 입력에 욕설, 비하, 공격적 표현이 포함된 경우 이를 무시하고 **건전한 텍스트**만 생성해주세요.
    - 욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.
    - 출력에는 절대 이모지(emoji)를 포함하지 마세요.
    - 출력에 줄바꿈 기호(`\\n`)나 실제 줄바꿈(Enter)을 포함하지 마세요.

    다음 모임 정보를 바탕으로 아래 두 항목을 생성해주세요:

    1. 한 줄 소개 (50자 이내): 모임의 핵심 목적을 간결하고 명확하게 요약한 한 문장입니다. 반드시 **명사형**으로 끝나야 하며, 한 문장으로 작성해주세요.

    2. 상세 설명 (400자 이내): 다음 형식을 따릅니다.
    - 처음 1~2문장은 자연스러운 소개 문단 형식으로 작성해주세요.
    - 이후 필요하다고 판단되면 **불릿 포인트** 형식으로 주요 활동, 운영 방식 등을 나열해주세요.
    - 불릿이 불필요하다고 판단되면 생략해도 괜찮습니다. 
    - 불릿이 포함된다면 각 줄은 `-`로 시작하며, 간결하게 한 문장으로 작성해주세요. 들여쓰기도 해주세요.
    
    출력 예시:
    한 줄 소개:
    LangChain 실습 중심의 생성형 AI 초보자 스터디
    
    출력 예시:
    상세 설명:
    LangChain 스터디는 생성형 AI를 배우고 싶은 초보자를 위한 실습 중심 스터디입니다.
    LangChain 공식 문서가 어렵거나 포트폴리오가 필요한 분들께 추천해요.
        - 매주 1회 오프라인/온라인 스터디 (2시간)
        - 사전 학습 자료 및 실습 과제 제공
        - 실습 위주의 코드 중심 스터디
        - 주차기말과제로 LangChain 미니 프로젝트 진행

    입력 정보:
    - 모임명: {data.name}
    - 목적: {data.goal}
    - 카테고리: {data.category}
    - 기간: {data.period}
    """
    try:
        ai_logger.info("[AI] [요약 생성 시작]", extra={"meeting_name": data.name})
        response = gen_model.generate_content(prompt, generation_config=config_model)
        full_text = response.text

        parts = full_text.split("한 줄 소개:")
        if len(parts) < 2:
            ai_logger.warning("[AI] [파싱 실패] '한 줄 소개' 구간 없음", extra={"preview": full_text[:80]})
            return "", ""

        after_intro = parts[1]
        subparts = after_intro.split("상세 설명:")
        if len(subparts) < 2:
            ai_logger.warning("[AI] [파싱 실패] '상세 설명' 구간 없음", extra={"preview": full_text[:80]})
            return "", ""

        summary = subparts[0].strip()
        description = subparts[1].strip()

        ai_logger.info("[AI] [모임 소개 생성 완료]",
                       extra={"summary_length": len(summary), "description_length": len(description)})
        return summary, description

    except Exception as e:
        ai_logger.exception("[AI] [Vertex Gemini 소개 생성 실패]")
        return "", ""

if __name__ == "__main__":
    from src.schemas.v1.group_writer import GroupGenerationRequest

    data = GroupGenerationRequest(
        name= "주말 러닝 크루",
        goal= "매주 함께 뛰며 체력과 건강을 관리하기",
        category= "운동/건강",
        period= "3개월",
        isPlanCreated=False
    )

    summary, description = generate_description(data)
    print((summary))
    print((description))