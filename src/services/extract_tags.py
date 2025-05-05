from src.config import *
from google import genai
import json, re

client = genai.Client(api_key=GEMINI_KEY)

def extract_tags(text: str) -> list[str]:
    prompt = f"""
    당신은 한국어 텍스트에서 핵심 키워드를 추출하는 AI입니다.

    다음 조건을 지켜서 키워드를 추출하세요:
    
    1. 명사 중심 키워드로만 추출하세요. 불용어(예: 그리고, 또는, 등)는 제외합니다.
    2. 주제와 관련된 의미 있는 단어(예: 활동, 관심사, 서비스, 개발자 스터디 등)를 선정하세요. 각 키워드는 공백 대신 '_'로 태그 형태로 가공하세요.
    3. 각 키워드는 1~5어절 이내의 짧은 구문이어야 하며, 너무 일반적인 단어(예: "것", "이야기")는 피하세요.
    4. 출력은 반드시 JSON 배열 형식으로만 하세요. 예시: ["개발자_스터디", "오프라인_밋업", "커뮤니티_모임"]
    5. 총 키워드 3개~5개를 출력하세요.
    6. 결과 외 다른 문장은 포함하지 마세요. 
    예시 출력: ["개발자_스터디", "오프라인_밋업", "커뮤니티_모임"]
    
    아래 텍스트에서 키워드를 추출하세요:
    
    <텍스트 시작>
    {text}
    <텍스트 끝>
    """

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    raw_output = response.text.strip()

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return re.findall(r'"(.*?)"', raw_output)

if __name__ == "__main__":
    text = """
    네모는 개발자와 디자이너가 함께 모여 사이드 프로젝트를 진행하는 커뮤니티입니다.
    매주 오프라인에서 아이디어를 공유하고, 코드 리뷰와 디자인 피드백 세션을 통해 서로 성장합니다.
    관심 분야는 웹 개발, 인공지능, UX/UI 디자인입니다.
    """
    tags = extract_tags(text)
    print("📌 추출된 태그:", tags)