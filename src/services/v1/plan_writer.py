from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from src.config import TXTGEN_MODEL_ID
from src.schemas.v1.group_writer import GroupGenerationRequest


def generate_plan(data: GroupGenerationRequest) -> str:
    model = GenerativeModel(TXTGEN_MODEL_ID)
    config = GenerationConfig(
        temperature=0.75,
        top_p=0.95,
        top_k=40,
        max_output_tokens=1024,
    )

    prompt = f"""
    당신은 모임을 소개하는 AI 비서입니다.
    아래 모임 정보를 바탕으로, 모임의 '목적'을 중심으로 실현 가능한 활동 커리큘럼을 스텝별로 작성해주세요.

    주의:
    - 사용자의 입력이 부적절하거나 욕설이 포함되어 있을 경우, 이를 무시하고 건전한 텍스트만 생성하세요.
    - 욕설, 비하 표현, 공격적 단어는 절대 그대로 사용하지 마세요.
    - 출력에는 절대 이모지(emoji)를 포함하지 마세요.

    출력 조건:
    - 커리큘럼은 반드시 '모임의 목적'을 중심으로 작성하세요.
    - 전체 기간({data.period}) 동안 실행 가능한 단계 수로 제한해주세요.
    - 일반적으로 {data.period} 기간에 따라 1~8단계 이내가 적절합니다.
    - **실제 줄바꿈(엔터)은 절대 사용하지 마세요.**
    - 각 줄 끝에는 문자 그대로 두 개의 백슬래시와 소문자 n (`\\n`)을 넣어주세요.
    - 출력은 모두 **한 줄 문자열 형태**로 이어져야 하며, 프론트엔드에서 `\\n`으로 줄바꿈 처리할 예정입니다.

    출력 포맷 예시 (줄바꿈 없이 모두 한 줄 문자열로 이어서 출력):
    - Step: 1\\n- title: OT 및 목표 설정\\n- detail: 참가자 소개 및 전체 커리큘럼 안내\\n- Step: 2\\n- title: 기본 개념 이해\\n- detail: 목표 달성을 위한 핵심 개념 학습\\n

    입력 정보:
    - 모임명: {data.name}
    - 목적: {data.goal}
    - 카테고리: {data.category}
    - 기간: {data.period}
    """

    try:
        response = model.generate_content(prompt, generation_config=config)
        return response.text.strip()
    except Exception as e:
        print(f"[Vertex Gemini 단계별 계획 생성 실패] {str(e)}")
        return ""

if __name__ == "__main__":
    import src.core.vertex_client
    from src.schemas.v1.group_writer import GroupGenerationRequest

    data = GroupGenerationRequest(
        name="딥러닝 실전 스터디",
        goal="딥러닝 기초 이론부터 실습까지 단계적으로 학습",
        category="학습/자기계발",
        period="4주",
        isPlanCreated=False
    )
    plan = generate_plan(data)
    print(repr(plan))