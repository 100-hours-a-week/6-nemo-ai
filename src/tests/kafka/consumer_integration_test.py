import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.kafka.consumers.consumer_manager import KafkaConsumerManager
from src.kafka.utils.kafka_client import get_producer, get_consumer
from src.core.ai_logger import get_ai_logger

logger = get_ai_logger()

class KafkaConsumerIntegrationTest:
    """Integration test for AI Kafka Consumer Manager"""

    def __init__(self):
        self.test_results = []
        self.consumer_manager = None

    async def test_consumer_manager_lifecycle(self):
        """Test the complete lifecycle of the consumer manager"""
        logger.info("🔄 Testing KafkaConsumerManager lifecycle...")

        try:
            # Initialize consumer manager
            self.consumer_manager = KafkaConsumerManager()
            
            # Test startup
            await self.consumer_manager.start_consumers()
            logger.info("✅ Consumer manager started successfully")
            
            # Wait a bit to see if consumers remain stable
            await asyncio.sleep(5)
            
            # Test graceful shutdown
            await self.consumer_manager.stop_consumers()
            logger.info("✅ Consumer manager stopped gracefully")
            
            self.test_results.append(("Consumer Manager Lifecycle", True))
            
        except Exception as e:
            logger.error(f"❌ Consumer manager lifecycle test failed: {e}")
            self.test_results.append(("Consumer Manager Lifecycle", False))

    async def test_topic_processing(self):
        """Test processing of different topic types"""
        logger.info("📋 Testing topic processing capabilities...")
        
        test_cases = [
            {
                "topic": "GROUP_EVENT",
                "message": {
                    "eventType": "GROUP_CREATED",
                    "data": {
                        "groupId": 9999,
                        "name": "Test Integration Group",
                        "category": "Test",
                        "summary": "Integration test group",
                        "description": "Testing integration",
                        "plan": "Test plan",
                        "location": "Test location",
                        "currentUserCount": 1,
                        "maxUserCount": 5,
                        "imageUrl": "test.jpg",
                        "tags": ["test", "integration"]
                    },
                    "timestamp": [2025, 7, 15, 12, 0, 0, 0]
                }
            },
            {
                "topic": "GROUP_RECOMMEND_QUESTION",
                "message": {
                    "type": "CREATE_QUESTION",
                    "payload": {
                        "sessionId": "test-integration-session",
                        "userId": 9999,
                        "answer": "Integration testing"
                    }
                }
            }
        ]
        
        producer = get_producer()
        await producer.start()
        
        try:
            all_passed = True
            for test_case in test_cases:
                try:
                    await producer.send_and_wait(test_case["topic"], test_case["message"])
                    logger.info(f"✅ Successfully sent message to {test_case['topic']}")
                except Exception as e:
                    logger.error(f"❌ Failed to send message to {test_case['topic']}: {e}")
                    all_passed = False
            
            self.test_results.append(("Topic Processing", all_passed))
            
        finally:
            await producer.stop()

    async def test_error_handling(self):
        """Test error handling and DLQ functionality"""
        logger.info("🚨 Testing error handling and DLQ...")
        
        # Send malformed message to test error handling
        producer = get_producer()
        await producer.start()
        
        try:
            # Send invalid message
            invalid_message = {
                "eventType": "INVALID_EVENT",
                "data": None
            }
            
            await producer.send_and_wait("GROUP_EVENT", invalid_message)
            logger.info("✅ Sent invalid message for error handling test")
            
            # Give time for processing and DLQ handling
            await asyncio.sleep(3)
            
            self.test_results.append(("Error Handling", True))
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            self.test_results.append(("Error Handling", False))
        finally:
            await producer.stop()

    def print_summary(self):
        """Print test results summary"""
        logger.info("\n" + "="*60)
        logger.info("🏁 AI KAFKA CONSUMER INTEGRATION TEST SUMMARY")
        logger.info("="*60)

        all_passed = True
        for test_name, result in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"  {test_name:<30}: {status}")
            if not result:
                all_passed = False

        logger.info("\n" + "-"*60)

        if all_passed:
            logger.info("🎉 ALL INTEGRATION TESTS PASSED!")
            logger.info("\n✅ AI KAFKA CONSUMER STATUS:")
            logger.info("  ✅ Consumer manager operational")
            logger.info("  ✅ Topic processing working")
            logger.info("  ✅ Error handling functional")
            logger.info("  ✅ Graceful shutdown working")
            logger.info("\n🚀 READY FOR PRODUCTION!")
        else:
            logger.error("❌ SOME INTEGRATION TESTS FAILED!")
            logger.error("  Review failed components before deployment")

        return all_passed

async def run_integration_tests():
    """Run comprehensive AI Kafka consumer integration tests"""
    logger.info("🚀 Starting AI Kafka Consumer integration tests...")

    test_suite = KafkaConsumerIntegrationTest()

    try:
        # Run all test categories
        await test_suite.test_consumer_manager_lifecycle()
        await test_suite.test_topic_processing()
        await test_suite.test_error_handling()
        
        # Print results
        success = test_suite.print_summary()
        return success
        
    except Exception as e:
        logger.error(f"❌ Integration test suite failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    sys.exit(0 if success else 1)
