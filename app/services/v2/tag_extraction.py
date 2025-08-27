import json
import re
# from app.core.cloud_logging import logger
from app.models.text_generation_model import call_vllm_api   # 로컬 모델로 교체
from app.core.ai_logger import get_ai_logger
from app.prompts.prompt_loader import load_prompt_template

ai_logger = get_ai_logger()


def _get_fallback_tags(text: str) -> list[str]:
    """Generate fallback tags when AI extraction fails"""
    # Extract potential tags using simple keyword matching
    common_meeting_keywords = {
        "고양이": ["고양이", "반려동물", "펫"],
        "맛집": ["맛집", "식당", "음식"],
        "운동": ["운동", "헬스", "피트니스"],
        "책": ["독서", "책", "문학"],
        "여행": ["여행", "관광", "탐방"],
        "게임": ["게임", "오락", "취미"],
        "음악": ["음악", "노래", "공연"],
        "영화": ["영화", "시네마", "영상"],
        "스터디": ["스터디", "학습", "공부"],
        "친목": ["친목", "모임", "교류"],
        "개발": ["개발", "프로그래밍", "코딩"],
        "디자인": ["디자인", "창작", "아트"],
        "사진": ["사진", "촬영", "포토"],
        "카페": ["카페", "커피", "디저트"]
    }
    
    fallback_tags = []
    text_lower = text.lower()
    
    # Try to match keywords from text
    for keyword, related_tags in common_meeting_keywords.items():
        if keyword in text:
            fallback_tags.extend(related_tags[:2])  # Add up to 2 related tags
            break
    
    # If no specific matches, use generic meeting tags
    if not fallback_tags:
        fallback_tags = ["모임", "활동", "소통"]
    
    return fallback_tags[:3]  # Return up to 3 fallback tags

async def extract_tags(text: str) -> list[str]:
    prompt = load_prompt_template("tag_extraction", "v2", text=text)

    try:
        ai_logger.info("[AI-v2] [태그 추출 시작]", extra={"text_length": len(text)})
        response = await call_vllm_api(prompt, max_tokens=128, temperature=0.2)
        raw = response.strip()

        try:
            tags = json.loads(raw)
        except json.JSONDecodeError:
            ai_logger.info("[AI-v2] [JSON 파싱 실패] 태그 정규식으로 대체 처리", extra={"raw_preview": raw[:80]})
            
            # Try multiple parsing strategies for the current model's output
            tags = []
            
            # Strategy 1: Extract from Korean patterns like [태그1], [태그2]
            bracket_tags = re.findall(r'\[([^\]]+)\]', raw)
            if bracket_tags:
                # Filter out meta descriptions like "추출된 키워드", "태그"
                filtered_tags = [tag for tag in bracket_tags 
                               if tag not in ["추출된 키워드", "태그", "키워드"] and len(tag) <= 10]
                tags.extend(filtered_tags)
            
            # Strategy 2: Look for quoted strings
            quoted_tags = re.findall(r'"([^"]+)"', raw)
            if quoted_tags:
                filtered_quoted = [tag for tag in quoted_tags 
                                 if tag not in ["추출된 키워드", "태그", "키워드"] and len(tag) <= 10]
                tags.extend(filtered_quoted)
            
            # Strategy 3: Extract Korean nouns from comma-separated or line-separated text
            if not tags:
                # Remove common phrases and extract meaningful Korean words
                cleaned = re.sub(r'\[.*?\]|추출된 키워드|태그|키워드|다음과 같습니다|결과|입니다', '', raw)
                # Split by common delimiters and clean
                potential_tags = re.split(r'[,\n\r\t\s]+', cleaned)
                for tag in potential_tags:
                    tag = tag.strip('[]()":., \n\r\t')
                    # Korean noun pattern: 1-5 syllables, meaningful content
                    if (re.match(r'^[가-힣]{1,5}$', tag) and 
                        tag not in ["그리고", "또는", "등", "이", "그", "저", "의", "를", "을", "가", "이"]):
                        tags.append(tag)
            
            # Remove duplicates while preserving order
            seen = set()
            tags = [tag for tag in tags if not (tag in seen or seen.add(tag))]
            
            # Limit to 3-5 tags as specified in prompt
            tags = tags[:5]

        # Strip periods from all tags
        cleaned_tags = []
        for tag in tags:
            if isinstance(tag, str):
                # Remove trailing periods and whitespace
                cleaned_tag = tag.rstrip('. \n\r\t')
                if cleaned_tag:  # Only add non-empty tags
                    cleaned_tags.append(cleaned_tag)

        ai_logger.info("[AI-v2] [태그 추출 완료]", extra={"tag_count": len(cleaned_tags)})
        
        # Validate tags and provide fallback if needed
        if not cleaned_tags or len(cleaned_tags) == 0:
            ai_logger.warning("[AI-v2] [태그 추출 실패] 폴백 태그 사용")
            return _get_fallback_tags(text)
        
        # Ensure we have 3-5 tags as required
        if len(cleaned_tags) < 3:
            fallback_tags = _get_fallback_tags(text)
            cleaned_tags.extend(fallback_tags[:5-len(cleaned_tags)])
        
        return cleaned_tags[:5]  # Limit to max 5 tags

    except Exception as e:
        ai_logger.exception("[AI-v2] [로컬모델 태그 추출 실패]")
        return []


if __name__ == "__main__":
    sample_text = """미야옹즈는 사랑스러운 고양이들과 함께하는 일상을 공유하고, 서로에게 필요한 정보를 나누는 고양이 집사들의 모임입니다."""
    import asyncio
    async def run_test():
        tags = await extract_tags(sample_text)
        print(tags)
    asyncio.run(run_test())
