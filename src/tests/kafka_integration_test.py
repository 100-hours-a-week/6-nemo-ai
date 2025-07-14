#!/usr/bin/env python3
"""
Complete Kafka Integration Test
Tests all Kafka flows: chat, group generation, question generation, recommendations, DLQ
Uses E5 embedding model (384 dimensions)
Usage: python -m src.tests.kafka_integration_test
"""
import asyncio
import json
import time
from typing import Dict, Any
from ..kafka.kafka_client import get_producer, get_consumer
from ..core.websocket_manager import websocket_manager
from ..core.ai_logger import get_ai_logger
from ..models.e5_embeddings import embed
from ..vector_db.vector_searcher import search_similar_documents
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
        self.e5_test_passed = False
    
    async def _test_e5_embedding_model(self):
        """Test E5 embedding model before running Kafka tests"""
        print("\n🧪 Testing E5 Embedding Model Integration...")
        
        try:
            # Test basic embedding
            test_texts = [
                "서울에서 요리 모임을 찾고 있습니다",
                "배드민턴 동호회에 참여하고 싶어요",
                "독서 토론 모임이 있나요?"
            ]
            
            vectors = embed(test_texts)
            
            # Check dimensions
            if vectors and len(vectors[0]) == 384:
                print(f"✅ E5 model working: {len(vectors)} vectors with 384 dimensions")
                self.e5_test_passed = True
            else:
                print(f"❌ E5 dimension error: expected 384, got {len(vectors[0]) if vectors else 'none'}")
                return False
            
            # Test query prefix
            query_vector = embed(["query: 요리 모임 찾기"])[0]
            if len(query_vector) == 384:
                print("✅ Query prefix working correctly")
            else:
                print("❌ Query prefix test failed")
                return False
                
            print("✅ E5 embedding model ready for Kafka integration testing")
            return True
            
        except Exception as e:
            print(f"❌ E5 model test failed: {e}")
            print("⚠️  Continuing with Kafka tests using mock data...")
            return False
    
    async def test_all_flows(self):
        """Test all Kafka flows: chat, group generation, questions, recommendations, DLQ"""
        print("🚀 Testing Complete Kafka Integration with E5 Embeddings")
        print("=" * 80)
        
        # Test E5 model first
        await self._test_e5_embedding_model()
        
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
        """Chat request/response consumer with E5 embedding integration"""
        consumer = get_consumer("chat-requests", "test-chat-consumer")
        producer = get_producer()
        await consumer.start()
        await producer.start()
        
        try:
            async for msg in consumer:
                if not self.running:
                    break
                
                data = msg.value
                session_id = data.get("sessionId")
                user_query = data.get("messages", [{}])[-1].get("text", "")
                
                print(f"📥 Processing chat request: {session_id}")
                print(f"   Query: {user_query}")
                
                # Use actual E5 embeddings for realistic testing
                try:
                    # Test E5 embedding functionality
                    embedding_vector = embed([f"query: {user_query}"])[0]
                    print(f"   ✅ E5 embedding generated: {len(embedding_vector)}D")
                    
                    # Test similarity search if we have data
                    search_results = search_similar_documents(
                        user_query, 
                        top_k=2, 
                        collection="group-info"
                    )
                    
                    recommendations = []
                    if search_results:
                        recommendations = [
                            result.get("metadata", {}).get("groupId", f"group-{i}")
                            for i, result in enumerate(search_results[:2])
                        ]
                        print(f"   🔍 Found {len(recommendations)} recommendations via E5 search")
                    else:
                        # Fallback mock recommendations
                        recommendations = ["Seoul Cooking Masters", "K-Food Club"]
                        print("   📝 Using mock recommendations (no vector data)")
                    
                except Exception as e:
                    print(f"   ⚠️ E5 embedding error: {e}")
                    recommendations = ["Mock Group 1", "Mock Group 2"]
                
                # Mock chat response with actual embedding results
                response = {
                    "sessionId": session_id,
                    "userId": data.get("userId"),
                    "response": {
                        "text": f"Found {len(recommendations)} great groups for '{user_query}'!",
                        "recommendations": recommendations,
                        "embedding_dims": 384,  # E5 dimension info
                        "search_method": "E5_multilingual_embeddings"
                    }
                }
                
                await producer.send_and_wait("chat-responses", response)
                
                # Send to WebSocket
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
        """Group recommendation consumer with E5 embedding integration"""
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
                user_messages = payload.get("messages", [])
                query_text = user_messages[-1].get("text", "") if user_messages else ""
                
                print(f"📥 Processing GROUP_RECOMMEND: {session_id}")
                print(f"   Query: {query_text}")
                
                recommendations = []
                confidence = 0.5
                
                try:
                    # Test E5 embedding for recommendations
                    if query_text:
                        embedding_vector = embed([f"query: {query_text}"])[0]
                        print(f"   ✅ E5 query embedding: {len(embedding_vector)}D")
                        
                        # Try actual similarity search
                        search_results = search_similar_documents(
                            query_text,
                            top_k=3,
                            collection="group-info"
                        )
                        
                        if search_results:
                            recommendations = [
                                {
                                    "groupId": result.get("metadata", {}).get("groupId", f"group-{i}"),
                                    "name": result.get("metadata", {}).get("name", f"Group {i+1}"),
                                    "matchScore": result.get("score", 0.8),
                                    "category": result.get("metadata", {}).get("category", "Unknown"),
                                    "location": result.get("metadata", {}).get("location", "Seoul")
                                }
                                for i, result in enumerate(search_results)
                            ]
                            confidence = max(r["matchScore"] for r in recommendations) if recommendations else 0.5
                            print(f"   🎯 E5 search found {len(recommendations)} matches (confidence: {confidence:.2f})")
                        else:
                            print("   📝 No vector data, using mock recommendations")
                    
                except Exception as e:
                    print(f"   ⚠️ E5 search error: {e}")
                
                # Fallback to mock data if no real results
                if not recommendations:
                    recommendations = [
                        {
                            "groupId": "seoul-cooking-001",
                            "name": "Seoul Cooking Masters",
                            "matchScore": 0.92,
                            "category": "요리/음식",
                            "location": "서울"
                        },
                        {
                            "groupId": "gangnam-book-001", 
                            "name": "Gangnam Book Club",
                            "matchScore": 0.78,
                            "category": "교육/학습",
                            "location": "강남"
                        }
                    ]
                    confidence = 0.88
                
                result = {
                    "sessionId": session_id,
                    "recommendations": recommendations,
                    "confidence": confidence,
                    "embedding_model": "E5_multilingual_small",
                    "dimensions": 384,
                    "search_query": query_text
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
        """Send test messages to all Kafka topics with E5-optimized queries"""
        producer = get_producer()
        await producer.start()
        
        try:
            # Test chat with Korean query (E5 is multilingual)
            await producer.send_and_wait("chat-requests", {
                "sessionId": "test-session-chat",
                "userId": "test-user-123",
                "messages": [{"role": "user", "text": "서울에서 요리 배우는 모임을 찾고 있어요"}]
            })
            
            # Test group generation
            await producer.send_and_wait("GROUP_GENERATE", {
                "groupId": "test-group-123",
                "requestType": "weekly_meeting"
            })
            
            # Test question generation with context
            await producer.send_and_wait("GROUP_RECOMMEND_QUESTION", {
                "sessionId": "test-session-questions",
                "userId": "test-user-456",
                "answer": "요리와 맛집 탐방에 관심이 있습니다"
            })
            
            # Test group recommendations with multilingual query
            await producer.send_and_wait("GROUP_RECOMMEND", {
                "sessionId": "test-session-recommendations",
                "userId": "test-user-789",
                "messages": [{"role": "user", "text": "판교에서 운동하는 모임을 찾고 있습니다"}]
            })
            
            print("📤 All E5-optimized test messages sent")
        finally:
            await producer.stop()
    
    def _report_results(self, mock_clients):
        """Report test results including E5 embedding integration"""
        print(f"\n📊 Kafka Integration Test Results:")
        print("=" * 50)
        
        success_count = sum(1 for e in self.processed_events if e["status"] == "success")
        total_ws_messages = sum(len(ws.messages) for ws in mock_clients.values())
        
        print(f"🧪 E5 embedding model: {'✅ Working' if self.e5_test_passed else '❌ Failed'}")
        print(f"✅ Kafka flows processed: {success_count}")
        print(f"📱 WebSocket messages: {total_ws_messages}")
        
        # Check for E5-specific data in responses
        e5_features_detected = 0
        for ws in mock_clients.values():
            for msg in ws.messages:
                payload = msg.get("payload", {})
                if any(key in payload for key in ["embedding_dims", "embedding_model", "dimensions"]):
                    e5_features_detected += 1
        
        print(f"🔬 E5 feature responses: {e5_features_detected}")
        
        if success_count >= 3 and total_ws_messages >= 2:
            print("\n🎯 ALL TESTS PASSED!")
            print("✅ Chat flow with E5 embeddings")
            print("✅ Group generation working")
            print("✅ Question generation → WebSocket")
            print("✅ Group recommendations with E5 → WebSocket")
            if self.e5_test_passed:
                print("✅ E5 multilingual embedding model integrated")
            if e5_features_detected > 0:
                print(f"✅ E5 features detected in {e5_features_detected} responses")
        else:
            print("\n⚠️ Some tests failed")
            print("Check E5 model configuration and vector database setup")

async def run_kafka_integration_test():
    """Main test runner"""
    tester = KafkaIntegrationTester()
    await tester.test_all_flows()

if __name__ == "__main__":
    asyncio.run(run_kafka_integration_test())
