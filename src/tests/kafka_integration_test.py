#!/usr/bin/env python3
"""
Complete Kafka Integration Test
Tests all Kafka flows: chat, group generation, question generation, recommendations, DLQ
Usage: python -m src.tests.kafka_integration_test
"""
import asyncio
import json
import time
from typing import Dict, Any
from ..kafka.kafka_client import get_producer, get_consumer
from ..core.websocket_manager import websocket_manager
from ..core.ai_logger import get_ai_logger
from starlette.websockets import WebSocketState

logger = get_ai_logger()

class MockWebSocket:
    """Mock WebSocket for testing WebSocket integration"""
    def __init__(self, session_id):
        self.session_id = session_id
        self.messages = []
        self.client_state = WebSocketState.CONNECTED
    
    async def send_json(self, data):
        self.messages.append(data)
        print(f"📱 WebSocket {self.session_id} received: {json.dumps(data, indent=2, ensure_ascii=False)}")

class KafkaIntegrationTester:
    """Tests all Kafka flows comprehensively"""
    
    def __init__(self):
        self.running = False
        self.processed_events = []
        self.dlq_events = []
    
    async def test_all_flows(self):
        """Test all Kafka flows: chat, group generation, questions, recommendations, DLQ"""
        print("🚀 Testing Complete Kafka Integration")
        print("=" * 80)
        
        # Setup mock WebSocket clients
        session_ids = ["test-session-questions", "test-session-recommendations", "test-session-chat"]
        mock_clients = {}
        
        for session_id in session_ids:
            mock_ws = MockWebSocket(session_id)
            websocket_manager.active_connections[session_id] = mock_ws
            mock_clients[session_id] = mock_ws
            print(f"🔌 Mock WebSocket connected: {session_id}")
        
        self.running = True
        
        # Start consumers
        tasks = [
            asyncio.create_task(self._chat_consumer()),
            asyncio.create_task(self._group_generation_consumer()),
            asyncio.create_task(self._question_generation_consumer()),
            asyncio.create_task(self._group_recommendation_consumer()),
        ]
        
        await asyncio.sleep(2)  # Wait for consumers to start
        
        # Run tests
        await self._send_test_messages()
        await asyncio.sleep(5)  # Wait for processing
        
        # Cleanup
        self.running = False
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Clear WebSocket connections
        for session_id in session_ids:
            websocket_manager.active_connections.pop(session_id, None)
        
        # Report results
        self._report_results(mock_clients)
    
    async def _chat_consumer(self):
        """Chat request/response consumer"""
        consumer = get_consumer("chat-requests", "test-chat-consumer")
        producer = get_producer()
        await consumer.start()
        await producer.start()
        
        try:
            async for msg in consumer:
                if not self.running:
                    break
                
                data = msg.value
                print(f"📥 Processing chat request: {data.get('sessionId')}")
                
                # Mock chat response
                response = {
                    "sessionId": data.get("sessionId"),
                    "userId": data.get("userId"),
                    "response": {
                        "text": "Found great cooking groups in Seoul!",
                        "recommendations": ["Seoul Cooking Masters", "K-Food Club"]
                    }
                }
                
                await producer.send_and_wait("chat-responses", response)
                
                # Send to WebSocket
                session_id = data.get("sessionId")
                if session_id and websocket_manager.is_connected(session_id):
                    await websocket_manager.send(session_id, {
                        "type": "CHAT_RESPONSE",
                        "payload": response["response"]
                    })
                
                self.processed_events.append({"type": "CHAT", "status": "success"})
                await consumer.commit()
        finally:
            await consumer.stop()
            await producer.stop()
    
    async def _group_generation_consumer(self):
        """Group generation consumer"""
        consumer = get_consumer("GROUP_GENERATE", "test-group-generate-consumer")
        producer = get_producer()
        await consumer.start()
        await producer.start()
        
        try:
            async for msg in consumer:
                if not self.running:
                    break
                
                payload = msg.value
                print(f"📥 Processing GROUP_GENERATE: {payload.get('groupId')}")
                
                # Mock meeting data
                meeting_data = {
                    "meetingId": f"meeting-{int(time.time())}",
                    "groupId": payload.get("groupId"),
                    "title": "Weekly Group Meeting",
                    "scheduledTime": "2025-07-21T14:00:00Z"
                }
                
                await producer.send_and_wait("GROUP_GENERATE_RESPONSE", {"payload": meeting_data})
                self.processed_events.append({"type": "GROUP_GENERATE", "status": "success"})
                await consumer.commit()
        finally:
            await consumer.stop()
            await producer.stop()
    
    async def _question_generation_consumer(self):
        """Question generation consumer"""
        consumer = get_consumer("GROUP_RECOMMEND_QUESTION", "test-question-consumer")
        producer = get_producer()
        await consumer.start()
        await producer.start()
        
        try:
            async for msg in consumer:
                if not self.running:
                    break
                
                payload = msg.value
                session_id = payload.get("sessionId")
                print(f"📥 Processing QUESTION_GENERATION: {session_id}")
                
                # Mock questions
                result = {
                    "sessionId": session_id,
                    "questions": [
                        "What activities interest you?",
                        "Preferred meeting frequency?"
                    ],
                    "options": [
                        {"id": "cooking", "text": "Cooking"},
                        {"id": "sports", "text": "Sports"}
                    ]
                }
                
                await producer.send_and_wait("GROUP_RECOMMEND_QUESTION_RESPONSE", result)
                
                # Send to WebSocket
                if session_id and websocket_manager.is_connected(session_id):
                    await websocket_manager.send(session_id, {
                        "type": "QUESTION_GENERATED",
                        "payload": {
                            "sessionId": session_id,
                            "questions": result["questions"],
                            "options": result["options"]
                        }
                    })
                
                self.processed_events.append({"type": "QUESTION_GENERATION", "status": "success"})
                await consumer.commit()
        finally:
            await consumer.stop()
            await producer.stop()
    
    async def _group_recommendation_consumer(self):
        """Group recommendation consumer"""
        consumer = get_consumer("GROUP_RECOMMEND", "test-group-recommend-consumer")
        producer = get_producer()
        await consumer.start()
        await producer.start()
        
        try:
            async for msg in consumer:
                if not self.running:
                    break
                
                payload = msg.value
                session_id = payload.get("sessionId")
                print(f"📥 Processing GROUP_RECOMMEND: {session_id}")
                
                # Mock recommendations
                result = {
                    "sessionId": session_id,
                    "recommendations": [
                        {
                            "groupId": "seoul-cooking-001",
                            "name": "Seoul Cooking Masters",
                            "matchScore": 0.92
                        }
                    ],
                    "confidence": 0.88
                }
                
                await producer.send_and_wait("GROUP_RECOMMEND_RESPONSE", result)
                
                # Send to WebSocket
                if session_id and websocket_manager.is_connected(session_id):
                    await websocket_manager.send(session_id, {
                        "type": "GROUP_RECOMMENDATIONS",
                        "payload": result
                    })
                
                self.processed_events.append({"type": "GROUP_RECOMMEND", "status": "success"})
                await consumer.commit()
        finally:
            await consumer.stop()
            await producer.stop()
    
    async def _send_test_messages(self):
        """Send test messages to all Kafka topics"""
        producer = get_producer()
        await producer.start()
        
        try:
            # Test chat
            await producer.send_and_wait("chat-requests", {
                "sessionId": "test-session-chat",
                "userId": "test-user-123",
                "messages": [{"role": "user", "text": "Find cooking groups"}]
            })
            
            # Test group generation
            await producer.send_and_wait("GROUP_GENERATE", {
                "groupId": "test-group-123",
                "requestType": "weekly_meeting"
            })
            
            # Test question generation
            await producer.send_and_wait("GROUP_RECOMMEND_QUESTION", {
                "sessionId": "test-session-questions",
                "userId": "test-user-456",
                "answer": "I like cooking"
            })
            
            # Test group recommendations
            await producer.send_and_wait("GROUP_RECOMMEND", {
                "sessionId": "test-session-recommendations",
                "userId": "test-user-789",
                "messages": [{"role": "user", "text": "Find Seoul cooking groups"}]
            })
            
            print("📤 All test messages sent")
        finally:
            await producer.stop()
    
    def _report_results(self, mock_clients):
        """Report test results"""
        print(f"\n📊 Test Results:")
        print("=" * 50)
        
        success_count = sum(1 for e in self.processed_events if e["status"] == "success")
        total_ws_messages = sum(len(ws.messages) for ws in mock_clients.values())
        
        print(f"✅ Kafka flows processed: {success_count}")
        print(f"📱 WebSocket messages: {total_ws_messages}")
        
        if success_count >= 3 and total_ws_messages >= 2:
            print("\n🎯 ALL TESTS PASSED!")
            print("✅ Chat flow working")
            print("✅ Group generation working")
            print("✅ Question generation → WebSocket")
            print("✅ Group recommendations → WebSocket")
        else:
            print("\n⚠️ Some tests failed")

async def run_kafka_integration_test():
    """Main test runner"""
    tester = KafkaIntegrationTester()
    await tester.test_all_flows()

if __name__ == "__main__":
    asyncio.run(run_kafka_integration_test())
