#!/usr/bin/env python3
"""
Test script for vLLM reliability improvements
Tests retry logic, circuit breaker, and health monitoring
"""

import asyncio
import json
import time
from src.models.gemma_3_4b import (
    stream_vllm_response, 
    call_vllm_api, 
    get_vllm_health_metrics,
    start_health_monitoring
)
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()


async def test_health_monitoring():
    """Test health monitoring functionality"""
    print("🔍 Testing health monitoring...")
    
    # Start health monitoring
    await start_health_monitoring()
    
    # Wait for initial health check
    await asyncio.sleep(2)
    
    try:
        metrics = await get_vllm_health_metrics()
        print(f"✅ Health metrics retrieved successfully:")
        print(json.dumps(metrics, indent=2))
        return True
    except Exception as e:
        print(f"❌ Health monitoring failed: {e}")
        return False


async def test_streaming_with_timeout():
    """Test streaming functionality with timeout handling"""
    print("\n🌊 Testing streaming with timeout...")
    
    messages = [
        {"role": "system", "text": "당신은 한국어로 대화하는 친근한 챗봇입니다."},
        {"role": "user", "text": "안녕하세요! 간단한 인사말을 해주세요."}
    ]
    
    try:
        start_time = time.time()
        tokens_received = 0
        
        async for token in stream_vllm_response(messages):
            tokens_received += 1
            print(f"Token {tokens_received}: {token}")
            
            # Break after reasonable number of tokens for testing
            if tokens_received > 20:
                break
        
        duration = time.time() - start_time
        print(f"✅ Streaming test completed: {tokens_received} tokens in {duration:.2f}s")
        return True
        
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False


async def test_application_streaming():
    """Test streaming with actual application prompts that are failing"""
    print("\n🔍 Testing application-specific streaming...")
    
    # This is the exact prompt your application uses for question generation
    app_prompt = """
사용자의 모임 선호도를 파악하기 위한 첫 질문을 생성하세요.
당신은 질문을 생성을 하는 모임 추천을 위한 챗봇이지만, 이 단계에서는 추천하지 마세요.  
다음 질문은 한국어로 자연스럽고 친근한 말투로 작성해주세요.
질문은 일반 문장 형태로 먼저 출력되고, 옵션은 JSON 형태로 나중에 함께 출력됩니다.

- "**질문:**", "**options:**" 같은 접두어는 절대 쓰지 마세요. 그냥 질문 문장과 JSON만 출력하세요.
- "네, 알겠습니다", "질문을 만들어보겠습니다", "아", "**질문:**" 같은 서론을 절대 포함하지 마세요
- 절대로 "질문:" 또는 "**질문:**" 접두어로 시작하지 마세요. 바로 질문 문장으로 시작하세요.
- 질문은 반드시 **AI가 사용자에게 묻는 문장**이어야 합니다. 질문의 주어는 항상 '당신' 또는 생략된 2인칭 사용자입니다.
- 문장은 항상 **2인칭 대상에게 질문하는 형태**여야 하며, **AI는 조력자 역할**입니다.
- 서론 없이 질문은 **하나의 문장**으로, **75~120자** 길이의 **친근하고 자연스러운 말투**로 작성하세요.
- 자연스럽고 중립적인 말투로 질문을 시작하세요. (예: "모임에 참여하신다면 어떤 분위기를 선호하시나요?")
- 질문의 주제는 모임의 성격, 분위기, 활동 목적, 인원 수, 대화 스타일, 모임 빈도 등 다양하게 설정하세요.
- 반드시 **이전 질문과는 다른 주제나 방향**의 질문을 작성하세요.
- 문장 앞뒤가 매끄럽게 이어지도록 하며, **반말이나 명령형은 피하고**, 정중하고 부드러운 말투를 사용하세요.
- 선택지는 총 4개이며, **각각 1~3단어 이내의 표현으로 구성**하세요.
질문 다음에 바로 아래 JSON 형식으로 출력하세요: 
  "options": ["...", "...", "...", "..."]
""".strip()
    
    messages = [
        {"role": "system", "text": "당신은 한국어로 대화하는 친근한 모임 추천 챗봇입니다."},
        {"role": "user", "text": app_prompt}
    ]
    
    try:
        start_time = time.time()
        tokens_received = 0
        full_response = ""
        
        print("  📤 Sending application prompt...")
        print(f"  📏 Prompt length: {len(app_prompt)} characters")
        
        async for token in stream_vllm_response(messages):
            tokens_received += 1
            full_response += token
            print(f"  Token {tokens_received}: '{token}' (len={len(token)})")
            
            # Don't break early, let it complete to see the full response
            if tokens_received > 100:  # Safety limit
                print("  ⚠️  Breaking due to token limit")
                break
        
        duration = time.time() - start_time
        print(f"\n  📊 Results:")
        print(f"    Tokens received: {tokens_received}")
        print(f"    Duration: {duration:.2f}s")
        print(f"    Response length: {len(full_response)} chars")
        print(f"    Full response: '{full_response}'")
        
        if tokens_received == 0:
            print("  ❌ ZERO TOKENS - This is the exact issue!")
            return False
        elif tokens_received < 10:
            print("  ⚠️  Very few tokens - might be an issue")
            return False
        else:
            print("  ✅ Streaming worked with application prompt")
            return True
        
    except Exception as e:
        print(f"  ❌ Application streaming test failed: {e}")
        return False


async def test_endpoint_comparison():
    """Test both endpoints directly to compare behavior"""
    print("\n🔄 Testing endpoint comparison...")
    
    from src.config import vLLM_URL
    import httpx
    import json
    
    ec2_url = "http://3.39.105.108:8002/"
    colab_url = "https://enormous-cattle-literally.ngrok-free.app/"
    current_url = vLLM_URL
    
    print(f"  Current configured URL: {current_url}")
    print(f"  EC2 URL: {ec2_url}")
    print(f"  Colab URL: {colab_url}")
    
    # Simple test prompt
    test_messages = [
        {"role": "system", "content": "당신은 한국어로 대화하는 친근한 챗봇입니다."},
        {"role": "user", "content": "안녕하세요"}
    ]
    
    test_payload = {
        "messages": test_messages,
        "stream": True,
        "max_tokens": 50,
        "temperature": 0.7,
    }
    
    async def test_endpoint_direct(endpoint_url, endpoint_name):
        print(f"\n  🔌 Testing {endpoint_name} directly...")
        chat_url = f"{endpoint_url.rstrip('/')}/v1/chat/completions"
        
        try:
            timeout_config = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=None)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                async with client.stream("POST", chat_url, json=test_payload) as response:
                    print(f"    Status: {response.status_code}")
                    
                    if response.status_code != 200:
                        response_text = await response.aread()
                        print(f"    Error response: {response_text.decode()}")
                        return False
                    
                    token_count = 0
                    tokens = []
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            content = line[len("data:"):].strip()
                            if content == "[DONE]":
                                break
                            
                            try:
                                parsed = json.loads(content)
                                delta = parsed["choices"][0]["delta"]
                                token = delta.get("content", "")
                                if token:
                                    token_count += 1
                                    tokens.append(token)
                                    print(f"      Token {token_count}: '{token}'")
                                    
                                    if token_count >= 10:  # Limit for comparison
                                        break
                                        
                            except Exception as parse_error:
                                print(f"      Parse error: {parse_error}")
                    
                    full_response = "".join(tokens)
                    print(f"    Result: {token_count} tokens, '{full_response}'")
                    return token_count > 0
                    
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    # Test both endpoints
    ec2_result = await test_endpoint_direct(ec2_url, "EC2")
    colab_result = await test_endpoint_direct(colab_url, "Colab")
    
    print(f"\n  📊 Direct endpoint results:")
    print(f"    EC2: {'✅ Working' if ec2_result else '❌ Failed'}")
    print(f"    Colab: {'✅ Working' if colab_result else '❌ Failed'}")
    
    return ec2_result and colab_result


async def test_retry_logic():
    """Test retry logic with simple API call"""
    print("\n🔄 Testing retry logic...")
    
    try:
        start_time = time.time()
        result = await call_vllm_api("안녕하세요", max_tokens=50)
        duration = time.time() - start_time
        
        print(f"✅ API call successful in {duration:.2f}s")
        print(f"Response preview: {result[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False


async def test_circuit_breaker_behavior():
    """Test circuit breaker behavior by monitoring state changes"""
    print("\n⚡ Testing circuit breaker behavior...")
    
    try:
        # Get initial metrics
        initial_metrics = await get_vllm_health_metrics()
        circuit_state = initial_metrics["circuit_breaker"]["state"]
        
        print(f"Initial circuit breaker state: {circuit_state}")
        
        # Make a few test calls to see how circuit breaker behaves
        success_count = 0
        for i in range(3):
            try:
                await call_vllm_api(f"Test call {i+1}", max_tokens=20)
                success_count += 1
                print(f"  Call {i+1}: ✅ Success")
            except Exception as e:
                print(f"  Call {i+1}: ❌ Failed - {e}")
            
            # Check circuit breaker state after each call
            metrics = await get_vllm_health_metrics()
            current_state = metrics["circuit_breaker"]["state"]
            if current_state != circuit_state:
                print(f"  Circuit breaker state changed: {circuit_state} -> {current_state}")
                circuit_state = current_state
        
        final_metrics = await get_vllm_health_metrics()
        print(f"Final metrics:")
        print(f"  Success rate: {final_metrics['health']['success_rate']:.2%}")
        print(f"  Circuit state: {final_metrics['circuit_breaker']['state']}")
        print(f"  Queue status: {final_metrics['queue_status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Circuit breaker test failed: {e}")
        return False


async def test_concurrent_requests():
    """Test behavior under concurrent load"""
    print("\n🚀 Testing concurrent request handling...")
    
    async def make_test_request(request_id: int):
        try:
            start = time.time()
            result = await call_vllm_api(f"Request {request_id}", max_tokens=20)
            duration = time.time() - start
            return {"id": request_id, "success": True, "duration": duration}
        except Exception as e:
            return {"id": request_id, "success": False, "error": str(e)}
    
    # Create concurrent requests
    tasks = [make_test_request(i) for i in range(5)]
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        
        print(f"Concurrent test results: {successful} successful, {failed} failed")
        
        for result in results:
            if isinstance(result, dict):
                if result.get("success"):
                    print(f"  Request {result['id']}: ✅ {result['duration']:.2f}s")
                else:
                    print(f"  Request {result['id']}: ❌ {result.get('error', 'Unknown error')}")
            else:
                print(f"  Request: ❌ Exception: {result}")
        
        return successful > 0
        
    except Exception as e:
        print(f"❌ Concurrent test failed: {e}")
        return False


async def main():
    """Run all reliability tests"""
    print("🧪 Starting vLLM reliability tests...\n")
    
    tests = [
        ("Health Monitoring", test_health_monitoring),
        ("Basic Streaming", test_streaming_with_timeout),
        ("Application Streaming", test_application_streaming),
        ("Endpoint Comparison", test_endpoint_comparison),
        ("Retry Logic", test_retry_logic),
        ("Circuit Breaker", test_circuit_breaker_behavior),
        ("Concurrent Requests", test_concurrent_requests),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
        
        # Add delay between tests
        await asyncio.sleep(1)
    
    # Print summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! vLLM reliability improvements are working.")
    else:
        print("⚠️  Some tests failed. Please check the logs above.")


if __name__ == "__main__":
    asyncio.run(main())
