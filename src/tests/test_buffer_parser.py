#!/usr/bin/env python3
"""
Test script for the buffer parser functionality to demonstrate
how it removes "이전 질문" (previous question) patterns from text buffers.
"""

import asyncio
from src.core.buffer_parser import (
    BufferParser, 
    remove_previous_question_from_text, 
    clean_prompt_context
)
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()


def test_text_cleaning():
    """Test the basic text cleaning functionality"""
    print("🧹 Testing basic text cleaning...")
    
    test_cases = [
        {
            "name": "Korean context pattern",
            "input": '이전 질문: "어떤 모임을 선호하시나요?"\n사용자 답변: "운동 모임을 좋아합니다"\n\n그렇다면 어떤 종류의 운동을 선호하시나요?',
            "expected_contains": "그렇다면 어떤 종류의 운동을 선호하시나요?"
        },
        {
            "name": "English context pattern", 
            "input": 'Previous question: "What type of meeting do you prefer?"\nUser answer: "I like sports meetings"\n\nThen what kind of sports do you prefer?',
            "expected_contains": "Then what kind of sports do you prefer?"
        },
        {
            "name": "Mixed patterns",
            "input": '이전 질문: "취미가 무엇인가요?"\nUser answer: "독서를 좋아해요"\n\n독서 모임에 관심이 있으시군요!',
            "expected_contains": "독서 모임에 관심이 있으시군요!"
        },
        {
            "name": "No context pattern",
            "input": "모임에 참여하고 싶은 이유가 무엇인가요?",
            "expected_contains": "모임에 참여하고 싶은 이유가 무엇인가요?"
        }
    ]
    
    for case in test_cases:
        print(f"\n  📋 테스트: {case['name']}")
        print(f"    입력: {case['input'][:50]}{'...' if len(case['input']) > 50 else ''}")
        
        cleaned = remove_previous_question_from_text(case['input'])
        print(f"    결과: {cleaned[:50]}{'...' if len(cleaned) > 50 else ''}")
        
        if case['expected_contains'] in cleaned:
            print(f"    ✅ 성공: 예상 텍스트가 포함됨")
        else:
            print(f"    ❌ 실패: 예상 텍스트 '{case['expected_contains']}'가 결과에 없음")
    
    return True


def test_streaming_parser():
    """Test the streaming chunk parsing functionality"""
    print("\n🌊 Testing streaming parser...")
    
    # Simulate streaming chunks that contain context patterns
    test_stream = [
        "이전 ",
        "질문: ",
        '"어떤 활동을 ',
        '좋아하시나요?"',
        "\n사용자 ",
        "답변: ",
        '"운동을 좋아합니다"',
        "\n\n",
        "그렇다면 ",
        "어떤 종류의 ",
        "운동을 ",
        "선호하시나요?"
    ]
    
    parser = BufferParser()
    final_output = ""
    chunks_processed = 0
    
    print(f"  📦 처리할 청크 수: {len(test_stream)}")
    
    for i, chunk in enumerate(test_stream):
        print(f"    청크 {i+1}: '{chunk}'")
        
        processed_chunk, context_found = parser.parse_streaming_chunk(chunk)
        
        if processed_chunk is not None:
            chunks_processed += 1
            final_output += processed_chunk
            print(f"      → 처리됨: '{processed_chunk}' (컨텍스트 발견: {context_found})")
        else:
            print(f"      → 대기중 (컨텍스트 처리중)")
    
    print(f"\n  📊 결과:")
    print(f"    처리된 청크: {chunks_processed}/{len(test_stream)}")
    print(f"    최종 출력: '{final_output}'")
    
    expected = "그렇다면 어떤 종류의 운동을 선호하시나요?"
    if expected in final_output:
        print(f"    ✅ 성공: 예상 텍스트가 최종 출력에 포함됨")
        return True
    else:
        print(f"    ❌ 실패: 예상 텍스트 '{expected}'가 최종 출력에 없음")
        return False


def test_prompt_cleaning():
    """Test prompt cleaning functionality"""
    print("\n📝 Testing prompt cleaning...")
    
    test_prompt = """[QUESTION]
이전 질문: "어떤 모임을 선호하시나요?"
사용자 답변: "운동 모임을 좋아합니다"
이 정보를 참고해 다음 질문을 생성하세요.

당신은 질문을 생성하는 챗봇입니다.
- 질문은 자연스럽게 작성하세요.
- 선택지는 4개를 제공하세요.
"""
    
    print(f"  📋 원본 프롬프트:")
    print(f"    {test_prompt}")
    
    cleaned_prompt = clean_prompt_context(test_prompt)
    print(f"\n  🧹 정리된 프롬프트:")
    print(f"    {cleaned_prompt}")
    
    # Check if context patterns were removed
    context_patterns = ["이전 질문:", "사용자 답변:"]
    patterns_removed = all(pattern not in cleaned_prompt for pattern in context_patterns)
    
    if patterns_removed:
        print(f"    ✅ 성공: 모든 컨텍스트 패턴이 제거됨")
        return True
    else:
        print(f"    ❌ 실패: 일부 컨텍스트 패턴이 남아있음")
        return False


def test_edge_cases():
    """Test edge cases and corner scenarios"""
    print("\n🔍 Testing edge cases...")
    
    edge_cases = [
        {
            "name": "Empty input",
            "input": "",
            "should_handle": True
        },
        {
            "name": "Only whitespace",
            "input": "   \n\n  \t  ",
            "should_handle": True
        },
        {
            "name": "Very long context",
            "input": "이전 질문: " + "a" * 1000 + "\n실제 질문이 여기에 있습니다",
            "should_handle": True
        },
        {
            "name": "Multiple context patterns",
            "input": "이전 질문: \"첫 번째\"\n사용자 답변: \"답변\"\nPrevious question: \"Second\"\nUser answer: \"Answer\"\n\n실제 내용",
            "should_handle": True
        },
        {
            "name": "Context without separator",
            "input": "이전 질문: \"질문\" 사용자 답변: \"답변\" 바로 이어지는 내용",
            "should_handle": True
        }
    ]
    
    success_count = 0
    
    for case in edge_cases:
        print(f"\n  📋 테스트: {case['name']}")
        
        try:
            # Test with buffer parser
            parser = BufferParser()
            processed_chunk, context_found = parser.parse_streaming_chunk(case['input'])
            
            # Test with text cleaner
            cleaned = remove_previous_question_from_text(case['input'])
            
            print(f"    ✅ 성공: 에지 케이스 처리됨")
            print(f"      스트리밍 결과: {repr(processed_chunk) if processed_chunk else 'None'}")
            print(f"      텍스트 정리 결과: {repr(cleaned[:50]) + '...' if len(cleaned) > 50 else repr(cleaned)}")
            success_count += 1
            
        except Exception as e:
            if case['should_handle']:
                print(f"    ❌ 실패: 예외 발생 - {e}")
            else:
                print(f"    ✅ 예상된 실패: {e}")
                success_count += 1
    
    print(f"\n  📊 에지 케이스 결과: {success_count}/{len(edge_cases)} 성공")
    return success_count == len(edge_cases)


async def main():
    """Run all buffer parser tests"""
    print("🧪 시작: Buffer Parser 테스트\n")
    
    tests = [
        ("기본 텍스트 정리", test_text_cleaning),
        ("스트리밍 파서", test_streaming_parser),
        ("프롬프트 정리", test_prompt_cleaning),
        ("에지 케이스", test_edge_cases),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"실행 중: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ 테스트 '{test_name}' 실행 중 오류: {e}")
            results[test_name] = False
    
    # Print summary
    print(f"\n{'='*60}")
    print("테스트 요약")
    print('='*60)
    
    for test_name, success in results.items():
        status = "✅ 통과" if success else "❌ 실패"
        print(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    print(f"\n전체: {passed_tests}/{total_tests} 테스트 통과")
    
    if passed_tests == total_tests:
        print("🎉 모든 테스트가 통과했습니다! Buffer Parser가 정상 작동합니다.")
    else:
        print("⚠️  일부 테스트가 실패했습니다. 위의 로그를 확인해주세요.")
    
    # Show usage examples
    print(f"\n{'='*60}")
    print("사용 예시")
    print('='*60)
    
    example_text = '이전 질문: "모임 참여 경험이 있나요?"\n사용자 답변: "네, 여러 번 참여했어요"\n\n그렇다면 어떤 종류의 모임을 가장 선호하시나요?'
    
    print("📝 원본 텍스트:")
    print(f"   {example_text}")
    
    cleaned = remove_previous_question_from_text(example_text)
    print("\n🧹 정리된 텍스트:")
    print(f"   {cleaned}")
    
    print("\n💡 사용법:")
    print("   from src.core.buffer_parser import remove_previous_question_from_text")
    print("   cleaned_text = remove_previous_question_from_text(your_text)")


if __name__ == "__main__":
    asyncio.run(main())
