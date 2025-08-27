"""
Comprehensive Kafka integration tests.
Migrated from src/tests/kafka/comprehensive_test.py
"""

import asyncio
import pytest

# Import from app instead of src
try:
    from app.integrations.kafka.kafka_client import get_producer, get_consumer
    from app.core.ai_logger import get_ai_logger
except ImportError:
    pytest.skip("Kafka integration not available", allow_module_level=True)

logger = get_ai_logger()


@pytest.mark.integration
@pytest.mark.kafka
class TestKafkaComprehensive:
    """Comprehensive Kafka implementation validator."""

    def setup_method(self):
        """Setup for each test method."""
        self.test_results = []

    @pytest.mark.asyncio
    async def test_connectivity(self):
        """Test basic Kafka connectivity."""
        producer = get_producer()
        await producer.start()

        try:
            await producer.send_and_wait("test-connectivity", {"ping": "pong"})
            assert True, "Kafka connectivity successful"
        except Exception as e:
            pytest.fail(f"Kafka connectivity failed: {e}")
        finally:
            await producer.stop()

    @pytest.mark.asyncio
    async def test_consumer_processing(self):
        """Test that consumers can process messages."""
        producer = get_producer()
        consumer = get_consumer("GROUP_EVENT", "test-processing-consumer")

        await producer.start()
        await consumer.start()

        try:
            # Send a message
            test_message = {
                "eventType": "GROUP_JOINED",
                "data": {
                    "groupId": 999,
                    "name": "Consumer Test Group",
                    "category": "Test",
                    "summary": "Testing consumer processing",
                    "description": "Test description",
                    "plan": "Test plan",
                    "location": "Test location",
                    "currentUserCount": 1,
                    "maxUserCount": 5,
                    "imageUrl": "test.jpg",
                    "tags": ["test", "consumer"]
                },
                "timestamp": [2025, 7, 15, 12, 0, 0, 0]
            }

            await producer.send_and_wait("GROUP_EVENT", test_message)

            # Verify consumer can receive
            msg = await asyncio.wait_for(consumer.getone(), timeout=5.0)
            
            assert msg.value.get("eventType") == "GROUP_JOINED"
            await consumer.commit()

        finally:
            await consumer.stop()
            await producer.stop()


@pytest.mark.integration
@pytest.mark.kafka
def test_kafka_configuration():
    """Test Kafka configuration and setup - synchronous setup test."""
    try:
        # Test that we can import Kafka client functions
        from app.integrations.kafka.kafka_client import get_producer, get_consumer
        
        # Just verify that the functions exist and are callable
        # Don't actually call them since they need async context
        assert callable(get_producer)
        assert callable(get_consumer)
        
        # Test passed - functions are available and importable
        assert True
        
    except Exception as e:
        pytest.fail(f"Kafka configuration test failed: {e}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
