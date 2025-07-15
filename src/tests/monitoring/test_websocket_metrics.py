#!/usr/bin/env python3
"""
WebSocket & HTTP Testing for Prometheus Metrics
Test script to generate metrics for monitoring
"""

import asyncio
import websockets
import requests
import time
from datetime import datetime


def test_http_endpoints():
    """Test HTTP endpoints"""
    print("🌐 Testing HTTP endpoints...")
    
    endpoints = [
        "http://localhost:8000/",
        "http://localhost:8000/health", 
        "http://localhost:8000/ai/v2/chatbot/health",
        "http://localhost:8000/metrics"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"📤 Testing {endpoint}")
            response = requests.get(endpoint, timeout=5)
            print(f"📥 {endpoint.split('/')[-1] or '/'}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")


async def test_websocket_endpoint(url, name):
    """Test WebSocket endpoint"""
    try:
        print(f"🔗 Testing {name} WebSocket endpoint...")
        async with websockets.connect(url) as websocket:
            await websocket.send("test message")
            response = await websocket.recv()
            print(f"✅ {name} WebSocket test successful")
    except Exception as e:
        print(f"❌ {name} WebSocket test failed: {e}")


async def run_websocket_tests():
    """Run WebSocket tests"""
    tasks = [
        test_websocket_endpoint("ws://localhost:8000/ws/llm", "LLM"),
        test_websocket_endpoint("ws://localhost:8000/ws/chatbot", "Chatbot")
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


def run_load_test():
    """Generate load to create metrics"""
    print("🚀 Running load test to generate more metrics...")
    
    # Run some WebSocket tests
    for _ in range(3):
        asyncio.run(test_websocket_endpoint("ws://localhost:8000/ws/llm", "LLM"))


def main():
    """Main test function"""
    print("=" * 60)
    print("🎯 WebSocket & HTTP Testing for Prometheus Metrics")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now()}")
    print()
    
    # Test HTTP endpoints
    test_http_endpoints()
    print()
    
    # Test WebSocket endpoints
    asyncio.run(run_websocket_tests())
    print()
    
    # Run load test
    run_load_test()
    
    print()
    print("=" * 60)
    print("✅ Testing completed!")
    print("🔍 Check the following URLs for metrics:")
    print("   • Prometheus: http://localhost:9090")
    print("   • Grafana: http://localhost:3000 (admin/nemo_secure_2024)")
    print("   • Your app metrics: http://localhost:8000/metrics")
    print("=" * 60)


if __name__ == "__main__":
    main()
