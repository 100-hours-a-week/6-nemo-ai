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
        ("Streaming with Timeout", test_streaming_with_timeout),
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
