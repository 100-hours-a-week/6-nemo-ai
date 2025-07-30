import json
import logging
from src.models.gemma_3_4b import stream_vllm_response, get_vllm_health_metrics
from src.core.chat_cache import get_session_history
from src.core.similarity_filter import is_similar_to_any
from src.vector_db.vector_searcher import (
    search_similar_documents,
    RECOMMENDATION_THRESHOLD,
)
from src.vector_db.hybrid_search import hybrid_group_search
from src.core.ai_logger import get_ai_logger
from src.core.buffer_parser import BufferParser, remove_previous_question_from_text, clean_prompt_context
import time
import asyncio

ai_logger = get_ai_logger()

class PrefixParser:
    """Helper class to handle prefix removal in streaming responses"""
    
    def __init__(self, prefixes: list[str], max_prefix_length: int = 12):
        self.prefixes = prefixes
        self.max_prefix_length = max_prefix_length
        self.buffer = ""
        self.prefix_processed = False
    
    def process_chunk(self, chunk: str) -> str | None:
        """Process a chunk and return the cleaned text or None if still waiting for prefix"""
        # Handle empty input immediately
        if not chunk:
            if self.prefix_processed:
                return ""
            else:
                # For empty chunks during prefix detection, if buffer is also empty, return empty string
                if not self.buffer:
                    self.prefix_processed = True
                    return ""
                # Otherwise continue with existing logic
        
        # Clean control characters and problematic standalone characters
        original_chunk = chunk
        
        # Remove only problematic control characters
        import re
        chunk = re.sub(r'\\[nrt\\]', '', chunk)  # Remove escaped newlines, tabs, backslashes
        chunk = re.sub(r'[\n\r\t]', '', chunk)  # Remove actual newlines, tabs
        
        # Remove standalone problematic characters that appear in streaming
        # but keep them when they're part of actual content
        # Be more selective - only remove opening JSON structure, not quotes needed for parsing
        if chunk.strip() in ['{', '}', '{"', '{"options":', '/', '\\']:
            chunk = ''
        
        # Preserve original chunk for debugging
        if chunk != original_chunk:
            ai_logger.debug(f"[청크 정리] 원본: {repr(original_chunk)} → 정리됨: {repr(chunk)}")
        
        if self.prefix_processed:
            # After prefix is processed, only check for major prefix patterns at the beginning
            cleaned_chunk = chunk
            for prefix in self.prefixes:
                # Only remove prefix if it's clearly at the beginning of the chunk
                if cleaned_chunk.startswith(prefix):
                    cleaned_chunk = cleaned_chunk[len(prefix):].lstrip()
                    ai_logger.info(f"[중간 접두어 제거됨] 제거된 접두어: {prefix}")
                    break
            return cleaned_chunk if cleaned_chunk else None
        
        self.buffer += chunk
        
        # Check for complete prefix match at the beginning
        prefix_found = False
        prefix_length = 0
        
        for prefix in self.prefixes:
            if self.buffer.startswith(prefix):
                prefix_found = True
                prefix_length = len(prefix)
                ai_logger.debug(f"[접두어 발견] 매치된 접두어: {prefix}")
                break
        
        if prefix_found:
            remaining_text = self.buffer[prefix_length:].lstrip()
            self.prefix_processed = True
            ai_logger.info(f"[접두어 제거됨] 제거된 접두어: {self.buffer[:prefix_length]}")
            
            # Return the remaining text after prefix removal, or empty string if nothing remains
            return remaining_text
        else:
            # Check if buffer could be building up to a prefix
            could_be_prefix = any(
                prefix.startswith(self.buffer) and len(self.buffer) < len(prefix)
                for prefix in self.prefixes
            )
            
            # Special case: if buffer is empty after cleaning (e.g., only special chars), proceed
            if not self.buffer:
                self.prefix_processed = True
                ai_logger.info(f"[접두어 없음] 빈 버퍼로 일반 스트리밍 시작")
                return ""
            
            if could_be_prefix and len(self.buffer) < self.max_prefix_length:
                # Might be partial prefix, wait for more chunks
                ai_logger.debug(f"[접두어 대기] 현재 버퍼: {repr(self.buffer)}")
                return None
            else:
                # Not a prefix, start normal streaming with accumulated buffer
                self.prefix_processed = True
                ai_logger.info(f"[접두어 없음] 일반 스트리밍 시작, 버퍼: {repr(self.buffer)}")
                # Return the buffer - even if empty after cleaning
                return self.buffer

async def stream_question_chunks(answer: str | None, user_id: str, session_id: str):
    history = get_session_history(session_id)
    previous_ai_messages = [m["content"] for m in history.get_messages() if m["role"] == "AI"]
    previous_question = previous_ai_messages[-1] if previous_ai_messages else None

    prompt = generate_combined_prompt(answer, previous_question)
    ai_logger.info("[Prompt 생성 완료]", extra={"prompt": prompt})

    streamed_text = ""  # Original text with prefixes (for logging)
    cleaned_text = ""   # Cleaned text without prefixes (for processing)
    full_question = ""
    options_text = ""
    capturing_options = False
    first = True
    start_time = time.time()
    
    # Initialize prefix parser and buffer parser
    prefix_parser = PrefixParser(["**질문:**", "질문:", "**Question:**", "Question:"])
    buffer_parser = BufferParser()

    async for chunk in stream_vllm_response([
        {"role": "system", "text": "당신은 한국어로 대화하는 친근한 모임 추천 챗봇입니다."},
        {"role": "user", "text": prompt}
    ]):
        if first:
            ai_logger.debug(f"[vLLM 첫 chunk 수신] chunk: {repr(chunk)} (len={len(chunk)}) time {time.time() - start_time:.3f} sec")
            first = False

        streamed_text += chunk  # Keep original for logging

        # Use buffer parser to handle context repetition
        processed_chunk, context_found = buffer_parser.parse_streaming_chunk(chunk)
        
        if processed_chunk is None:
            continue  # Skip this chunk (waiting for context separator or processing)
        
        if context_found:
            ai_logger.info(f"[컨텍스트 처리됨] 버퍼 파서가 컨텍스트 반복을 처리함")
            # Reset other processing state when context is detected
            cleaned_text = ""
            full_question = ""
            options_text = ""
            capturing_options = False
            prefix_parser = PrefixParser(["**질문:**", "질문:", "**Question:**", "Question:"])
            chunk = processed_chunk
        else:
            chunk = processed_chunk

        # Process chunk through prefix parser
        processed_chunk = prefix_parser.process_chunk(chunk)
        if processed_chunk is None:
            continue  # Still waiting for complete prefix
        
        # Log the processing result for debugging
        if processed_chunk != chunk:
            ai_logger.debug(f"[청크 처리] 원본: {repr(chunk)} → 처리됨: {repr(processed_chunk)}")
        
        cleaned_text += processed_chunk  # Accumulate cleaned text
        chunk = processed_chunk  # Use the cleaned chunk
        
        # options가 시작되는 시점 파악
        if not capturing_options and "options" in chunk:
            capturing_options = True
            idx = chunk.find("options")
            # Add the part before options to full_question
            question_part = chunk[:idx]
            full_question += question_part
            options_text += chunk[idx:]

            # Send the question part if it's not empty
            if question_part:
                yield question_part
            continue

        if capturing_options:
            options_text += chunk  # stream은 멈추고 내부에서 buffer에 저장
        else:
            full_question += chunk
            # Send chunks
            if chunk:  # Send any non-empty chunk including spaces
                yield chunk

    end_time = time.time()
    ai_logger.debug(f"[질문 전체 응답 수신 완료] time {end_time - start_time:.3f} sec")
    if ai_logger.isEnabledFor(logging.DEBUG):
        ai_logger.debug(f"[원본 응답]: {repr(streamed_text.strip())}")
        ai_logger.debug(f"[정리된 응답]: {repr(cleaned_text.strip())}")

    try:
        options = extract_options_from_stream(options_text)

        if not options or len(options) < 2:
            raise ValueError("options 파싱 실패 또는 항목 부족")

        history.add_ai_message(full_question.strip())

        yield ("__COMPLETE__", {
            "question": None,
            "options": options
        })

    except Exception as e:
        ai_logger.warning("[질문 옵션 파싱 실패]", extra={"error": str(e), "raw": repr(options_text)})

        fallback = {
            "question": "다른 사람과 함께 하고 싶은 활동은 무엇인가요?",
            "options": ["문화 체험", "운동", "스터디", "봉사"]
        }
        yield ("__COMPLETE__", fallback)


def generate_combined_prompt(previous_answer: str | None, previous_question: str | None = None) -> str:
    context_lines = []
    if previous_question:
        context_lines.append(f"이전 질문: \"{previous_question}\"")
    if previous_answer:
        context_lines.append(f"사용자 답변: \"{previous_answer}\"")

    context = "\n".join(context_lines) + "\n이 정보를 참고해 다음 질문을 생성하세요." if context_lines else \
        "사용자의 모임 선호도를 파악하기 위한 첫 질문을 생성하세요."

    connect_instruction = (
        "- 질문은 이전 응답을 반영하여 **연결된 말투**로 시작하세요. (예: \"그렇군요, 그러면...\", \"아, 그런 스타일 좋아하시네요. 그렇다면...\")"
        if previous_question and previous_answer else
        "- 자연스럽고 중립적인 말투로 질문을 시작하세요. (예: \"모임에 참여하신다면 어떤 분위기를 선호하시나요?\")"
    )

    base_prompt = f"""[QUESTION]
{context}
당신은 질문을 생성을 하는 모임 추천을 위한 챗봇이지만, 이 단계에서는 추천하지 마세요.  
다음 질문은 한국어로 자연스럽고 친근한 말투로 작성해주세요.
질문은 일반 문장 형태로 먼저 출력되고, 옵션은 JSON 형태로 나중에 함께 출력됩니다.

- "**질문:**", "**options:**" 같은 접두어는 절대 쓰지 마세요. 그냥 질문 문장과 JSON만 출력하세요.
- "네, 알겠습니다", "질문을 만들어보겠습니다", "아", "**질문:**" 같은 서론을 절대 포함하지 마세요
- 절대로 "질문:" 또는 "**질문:**" 접두어로 시작하지 마세요. 바로 질문 문장으로 시작하세요.
- 질문은 반드시 **AI가 사용자에게 묻는 문장**이어야 합니다. 질문의 주어는 항상 '당신' 또는 생략된 2인칭 사용자입니다.
- 문장은 항상 **2인칭 대상에게 질문하는 형태**여야 하며, **AI는 조력자 역할**입니다.
- 서론 없이 질문은 **하나의 문장**으로, **75~120자** 길이의 **친근하고 자연스러운 말투**로 작성하세요.
{connect_instruction}
- 질문의 주제는 모임의 성격, 분위기, 활동 목적, 인원 수, 대화 스타일, 모임 빈도 등 다양하게 설정하세요.
- 반드시 **이전 질문과는 다른 주제나 방향**의 질문을 작성하세요.
- 문장 앞뒤가 매끄럽게 이어지도록 하며, **반말이나 명령형은 피하고**, 정중하고 부드러운 말투를 사용하세요.
- 선택지는 총 4개이며, **각각 1~3단어 이내의 표현으로 구성**하세요.
- 응답에서 "이전 질문:", "사용자 답변:" 등의 컨텍스트를 반복하지 마세요.
질문 다음에 바로 아래 JSON 형식으로 출력하세요: 
  "options": ["...", "...", "...", "..."]
""".strip()

    return clean_prompt_context(base_prompt)


async def stream_recommendation_chunks(messages: list[dict], user_id: str, session_id: str):
    if not messages:
        yield (-1, "대화 내용이 부족하여 추천을 생성할 수 없습니다.")
        return

    combined_text = "\n".join([f"{m['role']}: {m['text']}" for m in messages])

    # Log health metrics before recommendation
    try:
        health_metrics = await get_vllm_health_metrics()
        ai_logger.info("[추천 시작 전 vLLM 상태]", extra={"metrics": health_metrics})
    except Exception as e:
        ai_logger.warning(f"[vLLM 상태 확인 실패]: {e}")

    results = hybrid_group_search(combined_text, top_k=10, user_id=user_id)
    if not results:
        results = search_similar_documents(
            "",
            top_k=10,
            collection="group-info",
            user_id=user_id,
        )

    ai_logger.info("[검색 결과]", extra={
        "session_id": session_id,
        "user_id": user_id,
        "results_count": len(results) if results else 0,
        "best_score": results[0].get("score", 0) if results else None,
        "best_group_id": results[0].get("metadata", {}).get("groupId") if results else None,
        "threshold": RECOMMENDATION_THRESHOLD
    })

    if not results or results[0].get("score", 0) < RECOMMENDATION_THRESHOLD:
        ai_logger.warning("[추천 모임 없음]", extra={
            "session_id": session_id,
            "user_id": user_id,
            "results_count": len(results) if results else 0,
            "best_score": results[0].get("score", 0) if results else 0,
            "threshold": RECOMMENDATION_THRESHOLD
        })
        # Send the message as question chunks first
        message = "조건에 맞는 모임이 아직 없어요. 직접 비슷한 모임을 열어보는 건 어떨까요?"
        for char in message:
            yield (-1, char)
        # Then send Recommend done with proper -1 group_id
        yield ("RECOMMEND_DONE", -1, message)
        return

    top_result = results[0]
    group_id = int(top_result["metadata"]["groupId"])
    raw_group_text = top_result["text"]
    
    ai_logger.info("[추천 모임 선택됨]", extra={
        "session_id": session_id,
        "user_id": user_id,
        "group_id": group_id,
        "score": top_result.get("score", 0),
        "origin": top_result.get("origin", "unknown")
    })
    
    # Clean the group text to remove potential tags, code blocks, and unwanted formatting
    import re
    group_text = clean_group_text(raw_group_text)
    group_text = _clean_group_text_for_recommendation(group_text)

    prompt = f"""[RECOMMEND]
사용자와의 대화:
{combined_text}

추천할 모임:
{group_text.strip()}

위 모임을 사용자에게 추천하는 이유를 설명하세요.

중요한 규칙:
- 질문을 하지 마세요. 추천 이유만 설명하세요.
- 한국어로만 작성하세요. 영어 단어는 사용하지 마세요.
- 150~250자의 자연스럽고 친근한 설명을 작성하세요.
- "설명:", "추천 이유:" 같은 접두어 없이 바로 설명 문장으로 시작하세요.
- 사용자의 관심사와 모임의 특징을 연결해서 설명하세요.
- 마지막에 물음표(?)를 사용하지 마세요.
- 태그나 메타데이터는 언급하지 마세요.

예시 형식: "이 모임은 당신이 찾고 있는 [관심사]와 정말 잘 맞을 것 같아요. [모임의 특징]을 통해 [기대효과]를 얻으실 수 있을 거예요."
""".strip()

    messages_for_vllm = [
        {"role": "system", "text": "당신은 모임을 추천하는 한국어 챗봇입니다. 질문을 하지 말고 추천 이유만 설명하세요. 영어를 절대 사용하지 마세요. 태그나 메타데이터는 언급하지 마세요."},
        {"role": "user", "text": prompt}
    ]

    full_reason = ""
    first = True
    start_time = time.time()
    token_count = 0

    # Initialize prefix parser and buffer parser for recommendations
    prefix_parser = PrefixParser(["**설명:**", "설명:", "**Description:**", "Description:", "**추천:**", "추천:", "**태그:**", "태그:", "**tags:**", "tags:"])
    buffer_parser = BufferParser()

    try:
        async for chunk in stream_vllm_response(messages_for_vllm):
            if first:
                first_chunk_time = time.time()
                ai_logger.debug(
                    f"[추천 vLLM 첫 chunk 수신] chunk: {repr(chunk)} time {first_chunk_time - start_time:.3f} sec"
                )
                first = False

            # Use buffer parser to handle context repetition in recommendations
            processed_chunk, context_found = buffer_parser.parse_streaming_chunk(chunk)
            
            if processed_chunk is None:
                continue  # Skip this chunk (waiting for context separator or processing)
            
            if context_found:
                ai_logger.info(f"[추천 컨텍스트 처리됨] 버퍼 파서가 컨텍스트 반복을 처리함")
                chunk = processed_chunk
            else:
                chunk = processed_chunk

            # Process chunk through prefix parser
            processed_chunk = prefix_parser.process_chunk(chunk)
            if processed_chunk is None:
                continue  # Still waiting for complete prefix
            
            # Log the processing result for debugging
            if processed_chunk != chunk:
                ai_logger.debug(f"[추천 청크 처리] 원본: {repr(chunk)} → 처리됨: {repr(processed_chunk)}")
            
            chunk = processed_chunk  # Use the cleaned chunk

            full_reason += chunk
            token_count += 1
            
            # Send the cleaned chunk
            if chunk:
                yield (group_id, chunk)


        full_reason = full_reason.strip()
        end_time = time.time()
        total_time = end_time - start_time
        
        ai_logger.debug(
            f"[추천 응답 수신 완료] time {total_time:.3f} sec, tokens: {token_count}, "
            f"tokens/sec: {token_count/total_time:.2f}"
        )
        if ai_logger.isEnabledFor(logging.DEBUG):
            ai_logger.debug(f"[추천 전체 응답]: {full_reason}")
        yield ("RECOMMEND_DONE", group_id, None)

    except Exception as e:
        ai_logger.error("[추천 스트리밍 중 오류]", extra={
            "error": str(e), 
            "session_id": session_id,
            "group_id": group_id
        })
        
        # Provide fallback recommendation text
        fallback_reason = "선택하신 관심사와 취향을 바탕으로 이 모임을 추천드립니다. 비슷한 관심사를 가진 분들과 함께 즐거운 시간을 보내실 수 있을 것 같아요!"
        for char in fallback_reason:
            yield (group_id, char)
        yield ("RECOMMEND_DONE", group_id, fallback_reason)


def _clean_group_text_for_recommendation(raw_text: str) -> str:
    """Clean group text to remove tags and metadata for recommendation"""
    import re
    
    # Remove code blocks (``` ``` patterns)
    text = re.sub(r'```[^`]*```', '', raw_text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove common tag patterns
    text = re.sub(r'태그[:：]\s*[^\n]*', '', text)
    text = re.sub(r'tags[:：]\s*[^\n]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'#\w+', '', text)  # Remove hashtags
    text = re.sub(r'\[태그\][^\n]*', '', text)
    text = re.sub(r'\[tags\][^\n]*', '', text, flags=re.IGNORECASE)
    
    # Remove metadata patterns
    text = re.sub(r'메타데이터[:：][^\n]*', '', text)
    text = re.sub(r'metadata[:：][^\n]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'분류[:：]\s*[^\n]*', '', text)
    text = re.sub(r'category[:：]\s*[^\n]*', '', text, flags=re.IGNORECASE)
    
    # Remove repeated whitespace and clean up
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def clean_group_text(text: str) -> str:
    """General function to clean group text for parsing and processing"""
    import re
    
    if not text:
        return text
    
    # Remove code blocks (``` ``` patterns)
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove triple quotes blocks (''' ''' patterns)
    text = re.sub(r"'''[^']*'''", '', text, flags=re.DOTALL)
    text = re.sub(r"'''.*?'''", '', text, flags=re.DOTALL)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def parse_group_information(group_data: dict) -> dict:
    """Parse and clean group information from raw group data"""
    if not group_data:
        return group_data
    
    # Clean text fields that might contain unwanted formatting
    text_fields = ['name', 'summary', 'description', 'plan']
    
    for field in text_fields:
        if field in group_data and group_data[field]:
            group_data[field] = clean_group_text(group_data[field])
    
    # Clean tags if they exist
    if 'tags' in group_data and isinstance(group_data['tags'], list):
        group_data['tags'] = [clean_group_text(tag) for tag in group_data['tags'] if tag]
    
    return group_data





def _clean_group_text_for_recommendation(raw_text: str) -> str:
    """Clean group text to remove tags and metadata for recommendation"""
    import re
    
    # Remove code blocks (``` ``` patterns)
    text = re.sub(r'```[^`]*```', '', raw_text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove common tag patterns
    text = re.sub(r'태그[:：]\s*[^\n]*', '', text)
    text = re.sub(r'tags[:：]\s*[^\n]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'#\w+', '', text)  # Remove hashtags
    text = re.sub(r'\[태그\][^\n]*', '', text)
    text = re.sub(r'\[tags\][^\n]*', '', text, flags=re.IGNORECASE)
    
    # Remove metadata patterns
    text = re.sub(r'메타데이터[:：][^\n]*', '', text)
    text = re.sub(r'metadata[:：][^\n]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'분류[:：]\s*[^\n]*', '', text)
    text = re.sub(r'category[:：]\s*[^\n]*', '', text, flags=re.IGNORECASE)
    
    # Remove repeated whitespace and clean up
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def clean_group_text(text: str) -> str:
    """General function to clean group text for parsing and processing"""
    import re
    
    if not text:
        return text
    
    # Remove code blocks (``` ``` patterns)
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove triple quotes blocks (''' ''' patterns)
    text = re.sub(r"'''[^']*'''", '', text, flags=re.DOTALL)
    text = re.sub(r"'''.*?'''", '', text, flags=re.DOTALL)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def parse_group_information(group_data: dict) -> dict:
    """Parse and clean group information from raw group data"""
    if not group_data:
        return group_data
    
    # Clean text fields that might contain unwanted formatting
    text_fields = ['name', 'summary', 'description', 'plan']
    
    for field in text_fields:
        if field in group_data and group_data[field]:
            group_data[field] = clean_group_text(group_data[field])
    
    # Clean tags if they exist
    if 'tags' in group_data and isinstance(group_data['tags'], list):
        group_data['tags'] = [clean_group_text(tag) for tag in group_data['tags'] if tag]
    
    return group_data




def extract_options_from_stream(raw: str) -> list[str] | None:
    import re
    import json
    
    ai_logger.debug(f"[옵션 파싱 시작] raw 텍스트: {raw}")
    
    # Clean the raw text first
    cleaned_raw = raw.strip()
    
    # Strategy 1: Look for complete JSON with "options" key
    json_patterns = [
        r'"options"\s*:\s*(\[\s*"[^"]*"(?:\s*,\s*"[^"]*")*\s*\])',  # Standard JSON array
        r'"options"\s*:\s*(\[\s*["\'][^"\']*["\'](?:\s*,\s*["\'][^"\']*["\'])*\s*\])',  # Mixed quotes
        r'options["\']?\s*:\s*(\[\s*"[^"]*"(?:\s*,\s*"[^"]*")*\s*\])',  # No quotes around key
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, cleaned_raw, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                options_str = match.group(1)
                ai_logger.debug(f"[JSON 패턴 매치] 추출된 옵션 문자열: {options_str}")
                options = json.loads(options_str)
                if isinstance(options, list) and len(options) >= 2:
                    clean_options = [str(o).strip() for o in options if o and str(o).strip()]
                    if len(clean_options) >= 2:
                        ai_logger.info(f"[옵션 파싱 성공 - JSON] 옵션: {clean_options}")
                        return clean_options
            except json.JSONDecodeError as e:
                ai_logger.debug(f"[JSON 파싱 실패] 에러: {e}")
                continue
    
    # Strategy 2: Look for standalone array patterns (without "options" key)
    array_patterns = [
        r'\[\s*"([^"]+)"(?:\s*,\s*"([^"]+)")*\s*\]',  # ["option1", "option2", ...]
        r'\[\s*["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']+)["\'])*\s*\]',  # Mixed quotes
        r'\[\s*([^,\[\]]+)(?:\s*,\s*([^,\[\]]+))*\s*\]',  # Unquoted options
    ]
    
    for pattern in array_patterns:
        matches = re.findall(pattern, cleaned_raw, re.DOTALL)
        if matches:
            # Flatten the matches and filter out empty strings
            options = []
            for match_group in matches:
                if isinstance(match_group, tuple):
                    options.extend([opt.strip().strip('"\'') for opt in match_group if opt and opt.strip()])
                else:
                    options.append(match_group.strip().strip('"\''))
            
            if len(options) >= 2:
                ai_logger.info(f"[옵션 파싱 성공 - 배열] 옵션: {options}")
                return options
    
    # Strategy 3: Line-by-line parsing for numbered or bulleted lists
    lines = cleaned_raw.split('\n')
    list_options = []
    
    for line in lines:
        line = line.strip()
        # Match patterns like: 1. option, - option, • option, * option
        line_patterns = [
            r'^\d+\.\s*(.+)$',  # 1. option
            r'^[-•*]\s*(.+)$',  # - option, • option, * option
            r'^["\']([^"\']+)["\'](?:\s*,?\s*)*$',  # "option" or 'option'
        ]
        
        for pattern in line_patterns:
            match = re.match(pattern, line)
            if match:
                option = match.group(1).strip().strip('"\'').rstrip(',')
                if option and len(option) <= 50:  # Reasonable length check
                    list_options.append(option)
                break
    
    if len(list_options) >= 2:
        ai_logger.info(f"[옵션 파싱 성공 - 라인별] 옵션: {list_options}")
        return list_options
    
    # Strategy 4: Extract quoted strings as potential options
    quoted_strings = re.findall(r'["\']([^"\']{1,30})["\']', cleaned_raw)
    if len(quoted_strings) >= 2:
        # Filter out common non-option words
        stopwords = {'options', 'question', '질문', '선택', '답변', 'answer', 'choice'}
        filtered_options = [opt.strip() for opt in quoted_strings 
                          if opt.strip().lower() not in stopwords and len(opt.strip()) > 0]
        
        if len(filtered_options) >= 2:
            ai_logger.info(f"[옵션 파싱 성공 - 인용문] 옵션: {filtered_options[:4]}")  # Take first 4
            return filtered_options[:4]
    
    # Strategy 5: Comma-separated values (last resort)
    if ',' in cleaned_raw:
        # Look for the part that might contain comma-separated options
        potential_options = []
        for segment in cleaned_raw.split('\n'):
            if ',' in segment and not any(word in segment.lower() for word in ['question', '질문', 'prompt']):
                parts = [p.strip().strip('"\'') for p in segment.split(',')]
                valid_parts = [p for p in parts if p and 1 <= len(p) <= 20]
                if len(valid_parts) >= 2:
                    potential_options.extend(valid_parts)
        
        if len(potential_options) >= 2:
            ai_logger.info(f"[옵션 파싱 성공 - 쉼표 구분] 옵션: {potential_options[:4]}")
            return potential_options[:4]
    
    ai_logger.warning(f"[옵션 파싱 완전 실패] raw 텍스트: {raw}")
    return None

