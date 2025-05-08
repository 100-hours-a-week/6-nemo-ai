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
    아래 모임 정보를 바탕으로, 모임의 '목적'을 중심으로 실현 가능한 활동 커리큘럼을 단계별로 작성해주세요.

    주의사항:
    - 부적절한 표현이나 욕설은 무시하고 건전하고 명확한 텍스트만 생성해주세요.
    - 출력에는 이모지(emoji)를 절대 포함하지 마세요.
    - **절대 실제 줄바꿈(엔터)를 사용하지 말고**, 각 줄 끝에는 문자 그대로 두 개의 백슬래시와 소문자 n (`\\n`)을 넣어주세요.
    - 출력은 반드시 한 줄 문자열 형태로 이어져야 하며, 프론트엔드에서 `\\n`으로 줄바꿈 처리할 예정입니다.

    출력 형식 및 조건:
    - 각 단계는 다음 형식을 따르세요:
      - Step N: [제목]\\n- [설명 문장 1]\\n- [설명 문장 2]...\\n
    - 설명이 길 경우, 문장을 자연스럽게 나누어 `- `로 시작하는 여러 줄로 구성해주세요.
    - 전체 기간({data.period})을 고려하여 **1~8단계 이내**로 기간에 적합한 수로 제한하세요. 일반적으로 1~8단계를 넘지 않습니다.
    - 모임 기간은 '1주', '2주', '1개월', '3개월'과 같은 단위로 주어집니다. 일 단위가 아닙니다.
    - 각 단계는 의미 있는 단위로 구성하세요. 너무 작게 나누지 말고, 하나의 단계에 충분한 활동량이 담기도록 하세요.
    - 모든 내용은 반드시 모임의 **'목적' 중심**으로 작성해야 합니다.

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
        period="2주",
        isPlanCreated=False
    )
    plan = generate_plan(data)
    print(repr(plan))