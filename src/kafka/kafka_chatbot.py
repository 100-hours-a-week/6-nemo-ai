import asyncio
from typing import Any
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from src.kafka.kafka_client import get_consumer, get_producer
from src.core.ai_logger import get_ai_logger
from src.services.v2.chatbot import handle_answer_analysis, handle_combined_question
from src.services.v2.group_information import build_meeting_data
from src.vector_db.group_document_builder import build_group_document
from src.vector_db.user_document_builder import build_user_document
from src.vector_db.vector_indexer import add_documents_to_vector_db

logger = get_ai_logger()


async def _safe_send(producer: AIOKafkaProducer, topic: str, message: Any) -> None:
    await producer.send_and_wait(topic, message)

aSYNC_SLEEP = 0.1

async def process_chat_requests() -> None:
    consumer = get_consumer("chat-requests", "chatbot-consumer")
    producer = get_producer()
    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            data = msg.value
            try:
                response = await handle_answer_analysis(
                    data.get("messages", []),
                    data.get("userId"),
                    data.get("sessionId"),
                )
                await _safe_send(
                    producer,
                    "chat-responses",
                    {
                        "sessionId": data.get("sessionId"),
                        "userId": data.get("userId"),
                        "response": response,
                    },
                )
                await consumer.commit()
            except Exception as e:
                logger.warning("[Kafka] chat request processing failed", extra={"error": str(e)})
                await _safe_send(producer, "chat-responses-dlq", {"error": str(e), "payload": data})
    finally:
        await consumer.stop()
        await producer.stop()


async def process_group_events() -> None:
    consumer = get_consumer("GROUP_EVENT", "group-event-consumer")
    await consumer.start()
    try:
        async for msg in consumer:
            event = msg.value
            try:
                doc = build_group_document(event)
                add_documents_to_vector_db([doc], "group-info")
                await consumer.commit()
            except Exception as e:
                logger.warning("[Kafka] group event failed", extra={"error": str(e)})
    finally:
        await consumer.stop()


async def process_user_events() -> None:
    consumer = get_consumer("USER_EVENT", "user-event-consumer")
    await consumer.start()
    try:
        async for msg in consumer:
            event = msg.value
            try:
                docs = build_user_document(event.get("userId"), event.get("groupId"))
                add_documents_to_vector_db(docs, "user-activity")
                await consumer.commit()
            except Exception as e:
                logger.warning("[Kafka] user event failed", extra={"error": str(e)})
    finally:
        await consumer.stop()


async def process_group_generation_requests() -> None:
    consumer = get_consumer("GROUP_GENERATE", "group-generate-consumer")
    producer = get_producer()
    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            payload = msg.value
            try:
                data = await build_meeting_data(payload)
                await _safe_send(
                    producer,
                    "GROUP_GENERATE_RESPONSE",
                    {"payload": data.model_dump()},
                )
                await consumer.commit()
            except Exception as e:
                logger.warning("[Kafka] group generate failed", extra={"error": str(e)})
                await _safe_send(producer, "GROUP_GENERATE_DLQ", {"error": str(e), "payload": payload})
    finally:
        await consumer.stop()
        await producer.stop()


async def process_question_generation_requests() -> None:
    consumer = get_consumer("GROUP_RECOMMEND_QUESTION", "question-consumer")
    producer = get_producer()
    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            payload = msg.value
            try:
                result = await handle_combined_question(
                    payload.get("answer"),
                    payload.get("userId"),
                    payload.get("sessionId"),
                )
                await _safe_send(producer, "GROUP_RECOMMEND_QUESTION_RESPONSE", result)
                await consumer.commit()
            except Exception as e:
                logger.warning("[Kafka] question generation failed", extra={"error": str(e)})
                await _safe_send(producer, "GROUP_RECOMMEND_QUESTION_DLQ", {"error": str(e), "payload": payload})
    finally:
        await consumer.stop()
        await producer.stop()


async def process_group_recommendations() -> None:
    consumer = get_consumer("GROUP_RECOMMEND", "group-recommend-consumer")
    producer = get_producer()
    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            payload = msg.value
            try:
                result = await handle_answer_analysis(
                    payload.get("messages", []),
                    payload.get("userId"),
                    payload.get("sessionId"),
                )
                await _safe_send(
                    producer,
                    "GROUP_RECOMMEND_RESPONSE",
                    result,
                )
                await consumer.commit()
            except Exception as e:
                logger.warning("[Kafka] group recommend failed", extra={"error": str(e)})
                await _safe_send(producer, "GROUP_RECOMMEND_DLQ", {"error": str(e), "payload": payload})
    finally:
        await consumer.stop()
        await producer.stop()


async def monitor_dlq(dlq_topic: str, handler, target_topic: str) -> None:
    consumer = get_consumer(dlq_topic, f"{dlq_topic}-consumer")
    producer = get_producer()
    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            payload = msg.value
            try:
                result = await handler(payload)
                if result is not None:
                    await _safe_send(producer, target_topic, result)
                await consumer.commit()
            except Exception as e:
                logger.error("[Kafka] DLQ message failed", extra={"topic": dlq_topic, "error": str(e)})
    finally:
        await consumer.stop()
        await producer.stop()