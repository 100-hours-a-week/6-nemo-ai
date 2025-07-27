import json
from app.models.gemma_3_4b import stream_vllm_response, get_vllm_health_metrics
from app.core.chat_cache import get_session_history
from app.core.utils import is_similar_to_any
from app.database.vector.vector_searcher import (
    search_similar_documents,
    RECOMMENDATION_THRESHOLD,
)
from app.database.vector.hybrid_search import hybrid_group_search
from app.core.ai_logger import get_ai_logger
from app.prompts.prompt_loader import load_prompt_template
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
        # Only remove newlines and carriage returns, but preserve other formatting
        original_chunk = chunk
        chunk = chunk.replace('\n', '').replace('\r', '')
        
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
            
            # Return the remaining text after prefix removal
            return remaining_text if remaining_text else None
        else:
            # Check if buffer could be building up to a prefix
            could_be_prefix = any(
                prefix.startswith(self.buffer) and len(self.buffer) < len(prefix)
                for prefix in self.prefixes
            )
            
            if could_be_prefix and len(self.buffer) < self.max_prefix_length:
                # Might be partial prefix, wait for more chunks
                ai_logger.debug(f"[접두어 대기] 현재 버퍼: {repr(self.buffer)}")
                return None
            else:
                # Not a prefix, start normal streaming with accumulated buffer
                self.prefix_processed = True
                ai_logger.info(f"[접두어 없음] 일반 스트리밍 시작, 버퍼: {repr(self.buffer)}")
                # Return the buffer without additional cleaning to preserve formatting
                return self.buffer if self.buffer else None

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
    
    # Initialize prefix parser
    prefix_parser = PrefixParser(["**질문:**", "질문:", "**Question:**", "Question:"])

    async for chunk in stream_vllm_response([
        {"role": "system", "text": "당신은 한국어로 대화하는 친근한 모임 추천 챗봇입니다."},
        {"role": "user", "text": prompt}
    ]):
        if first:
            ai_logger.info(f"[vLLM 첫 chunk 수신] chunk: {repr(chunk)} (len={len(chunk)}) time {time.time() - start_time} sec")
            first = False

        streamed_text += chunk  # Keep original for logging

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
    ai_logger.info(f"[질문 전체 응답 수신 완료] time {end_time - start_time} sec")
    ai_logger.info(f"[원본 응답]: {repr(streamed_text.strip())}")
    ai_logger.info(f"[정리된 응답]: {repr(cleaned_text.strip())}")

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

    return load_prompt_template("ws_chatbot_question_generation", 
                                context=context, 
                                connect_instruction=connect_instruction)


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

    if not results or results[0].get("score", 0) < RECOMMENDATION_THRESHOLD:
        # Send the message as question chunks first
        message = "조건에 맞는 모임이 아직 없어요. 직접 비슷한 모임을 열어보는 건 어떨까요?"
        for char in message:
            yield (-1, char)
        # Then send Recommend done
        yield ("RECOMMEND_DONE", -1, None)
        return

    top_result = results[0]
    group_id = int(top_result["metadata"]["groupId"])
    group_text = top_result["text"]

    prompt = load_prompt_template("ws_chatbot_recommendation",
                                  conversation=combined_text,
                                  group_text=group_text.strip())

    messages_for_vllm = [
        {"role": "system", "text": "당신은 한국어로 대화하는 친절한 모임 추천 챗봇입니다. 영어를 절대 사용하지 마세요."},
        {"role": "user", "text": prompt}
    ]

    full_reason = ""
    first = True
    start_time = time.time()
    token_count = 0

    # Initialize prefix parser for recommendations
    prefix_parser = PrefixParser(["**설명:**", "설명:", "**Description:**", "Description:", "**추천:**", "추천:"])

    try:
        async for chunk in stream_vllm_response(messages_for_vllm):
            if first:
                first_chunk_time = time.time()
                ai_logger.info(
                    f"[추천 vLLM 첫 chunk 수신] chunk: {repr(chunk)} time {first_chunk_time - start_time:.3f} sec"
                )
                first = False

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
        
        ai_logger.info(
            f"[추천 응답 수신 완료] time {total_time:.3f} sec, tokens: {token_count}, "
            f"tokens/sec: {token_count/total_time:.2f}",
            extra={"full_reason": full_reason}
        )
        yield ("RECOMMEND_DONE", group_id, None)

    except Exception as e:
        ai_logger.error("[추천 스트리밍 중 오류]", extra={
            "error": str(e), 
            "session_id": session_id,
            "group_id": group_id
        })
        
        # Provide fallback recommendation text
        fallback_reason = "선택하신 관심사와 취향을 바탕으로 이 모임을 추천드립니다. 비슷한 관심사를 가진 분들과 함께 즐거운 시간을 보내실 수 있을 것 같아요!"
        yield (group_id, fallback_reason)
        yield ("RECOMMEND_DONE", group_id, None)

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

