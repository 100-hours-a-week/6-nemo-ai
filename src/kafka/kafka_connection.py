import asyncio
import json
import uuid

from src.kafka.kafka_client import get_producer, get_consumer

async def test_kafka_round_trip():
    topic = f"test-topic-{uuid.uuid4().hex}"
    group_id = f"test-group-{uuid.uuid4().hex}"

    producer = get_producer()
    consumer = get_consumer(topic, group_id)

    await producer.start()
    await consumer.start()

    try:
        test_message = {"ping": "pong"}

        await producer.send_and_wait(topic, test_message)

        try:
            msg = await asyncio.wait_for(consumer.getone(), timeout=5)
        except asyncio.TimeoutError:
            assert False, "Kafka consumer timed out after 5 seconds"

        received_value = msg.value
        assert received_value == test_message, f"Expected {test_message}, got {received_value}"

    finally:
        await consumer.stop()
        await producer.stop()
