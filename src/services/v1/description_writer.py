from typing import Tuple
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from src.config import TXTGEN_MODEL_ID
from src.schemas.v1.group_writer import GroupGenerationRequest

def generate_description(data: GroupGenerationRequest) -> Tuple[str, str]:
    model = GenerativeModel(TXTGEN_MODEL_ID)
    config = GenerationConfig(
        temperature=0.75,
        top_p=0.95,
        top_k=40,
        max_output_tokens=1024,
    )

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
     - 각 문장을 끝낼 때마다 반드시 `\\n`을 넣어 주세요. 문장 단위로 줄을 나눈 것처럼 작성해야 합니다.

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

    try:
        response = model.generate_content(prompt, generation_config=config)
        full_text = response.text
        full_text = full_text.replace('\n', '')

        parts = full_text.split("- 한 줄 소개:")
        if len(parts) < 2:
            print(f"[파싱 실패] '한 줄 소개' 구간 없음:\n{full_text}")
            return "", ""

        after_intro = parts[1]
        subparts = after_intro.split("- 상세 설명:")
        if len(subparts) < 2:
            print(f"[파싱 실패] '상세 설명' 구간 없음:\n{full_text}")
            return "", ""

        summary = subparts[0].strip()
        description = subparts[1].strip()

        return summary, description

    except Exception as e:
        print(f"[Vertex Gemini 소개 생성 실패] {str(e)}")
        return "", ""

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

    summary, description = generate_description(data)
    print(repr(summary))
    print(repr(description))