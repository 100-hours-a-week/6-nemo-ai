import asyncio
import json
from datetime import datetime
from typing import Any
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from src.kafka.kafka_client import get_consumer, get_producer
from src.core.ai_logger import get_ai_logger
from src.core.websocket_manager import websocket_manager
from src.services.v2.chatbot import handle_answer_analysis, handle_combined_question
from src.services.v2.group_information import build_meeting_data
from src.vector_db.group_document_builder import build_group_document
from src.vector_db.user_document_builder import build_user_document
from src.vector_db.vector_indexer import add_documents_to_vector_db
from src.schemas.v2.kafka_events import GroupEvent, GroupGenerateRequest, QuestionRequest, RecommendRequest, DLQMessage

logger = get_ai_logger()

async def _safe_send(producer: AIOKafkaProducer, topic: str, message: Any) -> None:
    """Safely send message to Kafka topic"""
    try:
        await producer.send_and_wait(topic, message)
        logger.info(f"[Kafka] Message sent to {topic}", extra={"message": message})
    except Exception as e:
        logger.error(f"[Kafka] Failed to send message to {topic}", extra={"error": str(e)})
        raise

async def _send_to_dlq(producer: AIOKafkaProducer, dlq_topic: str, original_message: dict, error: str) -> None:
    """Send failed message to Dead Letter Queue"""
    dlq_message = {
        "originalMessage": original_message,
        "errorType": "processing_failed",
        "errorMessage": str(error),
        "failedAt": datetime.now().isoformat(),
        "source": "AI-CONSUMER"
    }
    await _safe_send(producer, dlq_topic, dlq_message)

# Process GROUP_EVENT topic (ChromaDB updates)
async def process_group_events() -> None:
    """Process group events: GROUP_CREATED, GROUP_DELETED, GROUP_JOINED, GROUP_LEFT"""
    consumer = get_consumer("group-user-events", "group-event-consumer")
    producer = get_producer()
    
    await consumer.start()
    await producer.start()
    
    logger.info("[Kafka] Started group events consumer")
    
    try:
        async for msg in consumer:
            event_data = msg.value
            try:
                # Parse event according to tech spec
                event = GroupEvent(**event_data)
                
                if event.eventType == "GROUP_CREATED":
                    # Add group to ChromaDB
                    doc = build_group_document(event.data.dict())
                    add_documents_to_vector_db([doc], "group-info")
                    logger.info(f"[ChromaDB] Added group {event.data.groupId}")
                    
                elif event.eventType == "GROUP_DELETED":
                    # Remove group from ChromaDB
                    from src.vector_db.chroma_client import get_chroma_client
                    client = get_chroma_client()
                    col = client.get_or_create_collection("group-info")
                    col.delete(ids=[f"group-{event.groupId}"])
                    logger.info(f"[ChromaDB] Deleted group {event.groupId}")
                    
                elif event.eventType in ["GROUP_JOINED", "GROUP_LEFT"]:
                    # Update user activity
                    user_data = event.data
                    if event.eventType == "GROUP_JOINED":
                        docs = build_user_document(user_data.userId, user_data.groupId)
                        add_documents_to_vector_db(docs, "user-activity")
                        logger.info(f"[ChromaDB] Added user {user_data.userId} to group {user_data.groupId}")
                    else:  # GROUP_LEFT
                        from src.vector_db.chroma_client import get_chroma_client
                        client = get_chroma_client()
                        col = client.get_or_create_collection("user-activity")
                        col.delete(ids=[f"user-{user_data.userId}-{user_data.groupId}"])
                        logger.info(f"[ChromaDB] Removed user {user_data.userId} from group {user_data.groupId}")
                
                await consumer.commit()
                
            except Exception as e:
                logger.error("[Kafka] Group event processing failed", extra={"error": str(e), "event": event_data})
                await _send_to_dlq(producer, "group-user-events-dlq", event_data, str(e))
                await consumer.commit()  # Commit to avoid reprocessing
                
    except Exception as e:
        logger.error("[Kafka] Group events consumer crashed", extra={"error": str(e)})
    finally:
        await consumer.stop()
        await producer.stop()

# Process GROUP_GENERATE topic
async def process_group_generation_requests() -> None:
    """Process group auto-generation requests"""
    consumer = get_consumer("group-generate", "group-generate-consumer")
    producer = get_producer()
    
    await consumer.start()
    await producer.start()
    
    logger.info("[Kafka] Started group generation consumer")
    
    try:
        async for msg in consumer:
            payload = msg.value
            try:
                # Parse and validate request
                request = GroupGenerateRequest(**payload)
                
                # Generate group information using AI
                from src.schemas.v1.group_information import MeetingInput
                meeting_input = MeetingInput(
                    name=request.name,
                    goal=request.goal,
                    category=request.category,
                    period=request.period,
                    isPlanCreated=request.isPlanCreated
                )
                
                result = await build_meeting_data(meeting_input)
                
                # Send response back to backend
                await _safe_send(producer, "group-generate-response", {
                    "status": "SUCCESS",
                    "data": result.dict()
                })
                
                logger.info("[Kafka] Group generation completed successfully")
                await consumer.commit()
                
            except Exception as e:
                logger.error("[Kafka] Group generation failed", extra={"error": str(e), "payload": payload})
                await _send_to_dlq(producer, "group-generate-dlq", payload, str(e))
                
                # Send failure response
                await _safe_send(producer, "group-generate-response", {
                    "status": "FAILED",
                    "error": str(e)
                })
                
                await consumer.commit()
                
    except Exception as e:
        logger.error("[Kafka] Group generation consumer crashed", extra={"error": str(e)})
    finally:
        await consumer.stop()
        await producer.stop()

# Process GROUP_RECOMMEND_QUESTION topic
async def process_question_generation_requests() -> None:
    """Process question generation requests for recommendations"""
    consumer = get_consumer("group-recommend-question", "question-consumer")
    producer = get_producer()
    
    await consumer.start()
    await producer.start()
    
    logger.info("[Kafka] Started question generation consumer")
    
    try:
        async for msg in consumer:
            payload = msg.value
            try:
                request = QuestionRequest(**payload)
                
                # Generate question using existing logic
                result = await handle_combined_question(
                    payload["payload"].get("answer"),
                    payload["payload"].get("userId"),
                    payload["payload"].get("sessionId"),
                )
                
                # Send response
                await _safe_send(producer, "group-recommend-question-response", {
                    "type": "QUESTION_GENERATED",
                    "payload": result
                })
                
                # Also send to WebSocket for real-time delivery
                session_id = payload["payload"].get("sessionId")
                if session_id and websocket_manager.is_connected(session_id):
                    ws_message = {
                        "type": "QUESTION_GENERATED",
                        "payload": {
                            "sessionId": session_id,
                            "question": result.get("question"),
                            "options": result.get("options", [])
                        }
                    }
                    await websocket_manager.send(session_id, ws_message)
                    logger.info("[Kafka→WS] Question sent to WebSocket", extra={"sessionId": session_id})
                
                await consumer.commit()
                
            except Exception as e:
                logger.error("[Kafka] Question generation failed", extra={"error": str(e), "payload": payload})
                await _send_to_dlq(producer, "group-recommend-question-dlq", payload, str(e))
                await consumer.commit()
                
    except Exception as e:
        logger.error("[Kafka] Question generation consumer crashed", extra={"error": str(e)})
    finally:
        await consumer.stop()
        await producer.stop()

# Process GROUP_RECOMMEND topic
async def process_group_recommendations() -> None:
    """Process final group recommendation requests"""
    consumer = get_consumer("group-recommend", "group-recommend-consumer")
    producer = get_producer()
    
    await consumer.start()
    await producer.start()
    
    logger.info("[Kafka] Started group recommendation consumer")
    
    try:
        async for msg in consumer:
            payload = msg.value
            try:
                request = RecommendRequest(**payload)
                
                # Generate recommendations using existing logic
                result = await handle_answer_analysis(
                    payload["payload"].get("messages", []),
                    payload["payload"].get("userId"),
                    payload["payload"].get("sessionId"),
                )
                
                # Send response
                await _safe_send(producer, "group-recommend-response", {
                    "type": "RECOMMENDATION_RESULT",
                    "payload": result
                })
                
                # Also send to WebSocket for real-time delivery
                session_id = payload["payload"].get("sessionId")
                if session_id and websocket_manager.is_connected(session_id):
                    ws_message = {
                        "type": "GROUP_RECOMMENDATIONS",
                        "payload": {
                            "sessionId": session_id,
                            "recommendations": result.get("recommendations", []),
                            "reasoning": result.get("reasoning", ""),
                            "confidence": result.get("confidence", 0.8)
                        }
                    }
                    await websocket_manager.send(session_id, ws_message)
                    logger.info("[Kafka→WS] Recommendations sent to WebSocket", extra={"sessionId": session_id})
                
                await consumer.commit()
                
            except Exception as e:
                logger.error("[Kafka] Group recommendation failed", extra={"error": str(e), "payload": payload})
                await _send_to_dlq(producer, "group-recommend-dlq", payload, str(e))
                await consumer.commit()
                
    except Exception as e:
        logger.error("[Kafka] Group recommendation consumer crashed", extra={"error": str(e)})
    finally:
        await consumer.stop()
        await producer.stop()

# DLQ Monitor for automatic retry
async def monitor_dlq() -> None:
    """Monitor DLQ topics and retry failed messages"""
    dlq_topics = [
        "group-user-events-dlq",
        "group-generate-dlq", 
        "group-recommend-question-dlq",
        "group-recommend-dlq"
    ]
    
    consumers = []
    producer = get_producer()
    await producer.start()
    
    try:
        for topic in dlq_topics:
            consumer = get_consumer(topic, f"{topic}-monitor")
            await consumer.start()
            consumers.append((consumer, topic))
        
        logger.info("[Kafka] Started DLQ monitors")
        
        # Simple retry logic - in production you'd want more sophisticated backoff
        while True:
            for consumer, topic in consumers:
                try:
                    msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)
                    dlq_data = msg.value
                    
                    # Simple retry after 1 minute (in production use exponential backoff)
                    failed_at = datetime.fromisoformat(dlq_data.get("failedAt", ""))
                    if (datetime.now() - failed_at).total_seconds() > 60:
                        
                        # Retry original message
                        original_topic = topic.replace("-dlq", "")
                        await _safe_send(producer, original_topic, dlq_data["originalMessage"])
                        
                        logger.info(f"[DLQ] Retried message from {topic}")
                        await consumer.commit()
                        
                except asyncio.TimeoutError:
                    continue  # No messages in this DLQ
                except Exception as e:
                    logger.error(f"[DLQ] Error monitoring {topic}", extra={"error": str(e)})
            
            await asyncio.sleep(10)  # Check every 10 seconds
            
    except Exception as e:
        logger.error("[Kafka] DLQ monitor crashed", extra={"error": str(e)})
    finally:
        for consumer, _ in consumers:
            await consumer.stop()
        await producer.stop()
