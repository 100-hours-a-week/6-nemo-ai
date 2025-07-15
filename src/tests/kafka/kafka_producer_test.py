import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.kafka.kafka_client import get_producer
from src.core.ai_logger import get_ai_logger

logger = get_ai_logger()

class KafkaTestProducer:
    """
    Test producer for validating Kafka consumer functionality.
    THIS IS FOR TESTING ONLY - NOT FOR PRODUCTION USE.
    """
    
    def __init__(self):
        self.producer = None
    
    async def start(self):
        """Start the producer"""
        self.producer = get_producer()
        await self.producer.start()
        logger.info("[Test Producer] Started")
    
    async def stop(self):
        """Stop the producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("[Test Producer] Stopped")
    
    async def send_group_event_test(self):
        """Send test group event messages"""
        logger.info("[Test] Sending group event messages...")
        
        test_events = [
            {
                "eventType": "GROUP_CREATED",
                "data": {
                    "groupId": 999,
                    "name": "Test AI Consumer Group",
                    "category": "Technology",
                    "summary": "Testing Kafka consumer functionality",
                    "description": "This is a test group created to validate consumer processing",
                    "plan": "1. Test message consumption\n2. Validate processing\n3. Check logging",
                    "location": "Seoul, Korea",
                    "currentUserCount": 1,
                    "maxUserCount": 10,
                    "imageUrl": "test.jpg",
                    "tags": ["test", "kafka", "consumer"]
                },
                "timestamp": [2025, 7, 14, 12, 0, 0, 0]
            },
            {
                "eventType": "GROUP_JOINED",
                "data": {
                    "userId": 42,
                    "groupId": 999
                },
                "timestamp": [2025, 7, 14, 12, 5, 0, 0]
            },
            {
                "eventType": "GROUP_LEFT",
                "data": {
                    "userId": 42,
                    "groupId": 999
                },
                "timestamp": [2025, 7, 14, 12, 10, 0, 0]
            },
            {
                "eventType": "GROUP_DELETED",
                "groupId": 999,
                "timestamp": [2025, 7, 14, 12, 15, 0, 0]
            }
        ]
        
        for event in test_events:
            await self.producer.send_and_wait("GROUP_EVENT", event)
            logger.info(f"[Test] Sent {event['eventType']} event")
            await asyncio.sleep(1)  # Space out messages
    
    async def send_group_generation_test(self):
        """Send test group generation requests"""
        logger.info("[Test] Sending group generation request...")
        
        test_request = {
            "name": "AI Study Group",
            "goal": "Learn machine learning and AI technologies together",
            "category": "Education",
            "location": "Seoul, Korea",
            "period": "3 months",
            "maxUserCount": 20,
            "isPlanCreated": True
        }
        
        await self.producer.send_and_wait("GROUP_GENERATE", test_request)
        logger.info("[Test] Sent group generation request")
    
    async def send_question_generation_test(self):
        """Send test question generation requests"""
        logger.info("[Test] Sending question generation request...")
        
        test_request = {
            "type": "CREATE_QUESTION",
            "payload": {
                "sessionId": "test-session-123",
                "userId": 42,
                "answer": "I'm interested in technology groups focused on AI and machine learning"
            }
        }
        
        await self.producer.send_and_wait("GROUP_RECOMMEND_QUESTION", test_request)
        logger.info("[Test] Sent question generation request")
    
    async def send_recommendation_test(self):
        """Send test recommendation requests"""
        logger.info("[Test] Sending recommendation request...")
        
        test_request = {
            "type": "RECOMMEND_REQUEST",
            "payload": {
                "sessionId": "test-session-123",
                "userId": 42,
                "messages": [
                    {"role": "user", "text": "I want to join a group about AI"},
                    {"role": "assistant", "text": "What specific aspect of AI interests you?"},
                    {"role": "user", "text": "Machine learning and deep learning"}
                ]
            }
        }
        
        await self.producer.send_and_wait("GROUP_RECOMMEND", test_request)
        logger.info("[Test] Sent recommendation request")
    
    async def run_all_tests(self):
        """Run all test scenarios"""
        logger.info("🚀 Starting Kafka producer tests...")
        logger.info("📝 These messages will be consumed by your AI server")
        
        try:
            await self.start()
            
            # Run all test scenarios
            await self.send_group_event_test()
            await asyncio.sleep(2)
            
            await self.send_group_generation_test()
            await asyncio.sleep(2)
            
            await self.send_question_generation_test()
            await asyncio.sleep(2)
            
            await self.send_recommendation_test()
            
            logger.info("✅ All test messages sent successfully!")
            logger.info("📊 Check your AI server logs to see consumer processing")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise
        finally:
            await self.stop()

async def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 KAFKA PRODUCER TEST SCRIPT")
    print("=" * 60)
    print("⚠️  WARNING: This is for TESTING ONLY!")
    print("⚠️  Do NOT include this in main.py!")
    print("⚠️  This script simulates backend message production.")
    print("")
    print("📋 This will send test messages to:")
    print("   • GROUP_EVENT")
    print("   • GROUP_GENERATE")
    print("   • GROUP_RECOMMEND_QUESTION")
    print("   • GROUP_RECOMMEND")
    print("")
    print("🔄 Your AI server consumers should process these messages.")
    print("=" * 60)
    
    # Confirm before running
    response = input("Continue with test? (y/N): ")
    if response.lower() != 'y':
        print("❌ Test cancelled")
        return
    
    # Run the test
    producer = KafkaTestProducer()
    await producer.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
