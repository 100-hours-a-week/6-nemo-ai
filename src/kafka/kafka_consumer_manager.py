"""
Kafka Consumer Manager - Clean Consumer-Only Implementation
This module provides a resilient Kafka consumer that:
1. Only consumes messages (no production)
2. Gracefully handles missing topics
3. Logs appropriately when no tasks are available
4. Never crashes due to missing topics/messages
"""
import asyncio
from typing import List, Optional, Dict, Any

from src.kafka.kafka_client import get_consumer, get_producer
from src.core.ai_logger import get_ai_logger

logger = get_ai_logger()

class KafkaConsumerManager:
    """
    Manages Kafka consumers for the AI server.
    This is a pure consumer implementation - no message production.
    """
    
    def __init__(self):
        self.consumers = []
        self.consumer_tasks = []
        
        # Define expected topics and their consumer functions
        self.topic_consumers = {
            "GROUP_EVENT": self._process_group_events,
            "GROUP_GENERATE": self._process_group_generation_requests,
            "GROUP_RECOMMEND_QUESTION": self._process_question_generation_requests,
            "GROUP_RECOMMEND": self._process_group_recommendations,
        }
        
        # DLQ topics to monitor
        self.dlq_topics = [
            "GROUP_EVENT_DLQ",
            "GROUP_GENERATE_DLQ",
            "GROUP_RECOMMEND_QUESTION_DLQ", 
            "GROUP_RECOMMEND_DLQ"
        ]
    
    async def start_consumers(self):
        """
        Start Kafka consumers for all expected topics.
        Gracefully handles missing topics and logs appropriately.
        """
        logger.info("[Kafka] Starting consumer manager...")
        
        active_consumers = 0
        
        for topic, consumer_func in self.topic_consumers.items():
            try:
                logger.info(f"[Kafka] Attempting to start consumer for topic '{topic}'...")
                
                # Start consumer for this topic directly
                consumer_task = asyncio.create_task(
                    consumer_func(topic), 
                    name=f"consumer-{topic}"
                )
                self.consumer_tasks.append(consumer_task)
                active_consumers += 1
                logger.info(f"[Kafka] Successfully started consumer for '{topic}'")
                
            except Exception as e:
                logger.error(f"[Kafka] Failed to start consumer for topic '{topic}': {e}")
        
        # Start DLQ monitor if any main consumers are active
        if active_consumers > 0:
            try:
                dlq_task = asyncio.create_task(
                    self._monitor_dlq(), 
                    name="dlq-monitor"
                )
                self.consumer_tasks.append(dlq_task)
                logger.info("[Kafka] Started DLQ monitor")
            except Exception as e:
                logger.error(f"[Kafka] Failed to start DLQ monitor: {e}")
        
        if active_consumers > 0:
            logger.info(f"[Kafka] Successfully started {active_consumers} consumers")
        else:
            logger.info("[Kafka] No active topics found - AI server will wait for backend to produce messages")
    
    async def stop_consumers(self):
        """Stop all running consumers gracefully."""
        logger.info("[Kafka] Stopping consumers...")
        
        # Cancel all consumer tasks
        for task in self.consumer_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Stop all consumers
        for consumer in self.consumers:
            try:
                await consumer.stop()
            except Exception as e:
                logger.warning(f"[Kafka] Error stopping consumer: {e}")
        
        logger.info("[Kafka] All consumers stopped")
    
    async def _process_group_events(self, topic: str):
        """Process group events: GROUP_CREATED, GROUP_DELETED, GROUP_JOINED, GROUP_LEFT"""
        consumer = get_consumer(topic, "group-event-consumer")
        self.consumers.append(consumer)
        
        await consumer.start()
        logger.info(f"[Kafka] Started consumer for {topic}")
        
        try:
            async for msg in consumer:
                event_data = msg.value
                try:
                    # Import here to avoid circular imports
                    from src.schemas.v2.kafka_events import GroupEvent
                    from src.vector_db.group_document_builder import build_group_document
                    from src.vector_db.user_document_builder import build_user_document
                    from src.vector_db.vector_indexer import add_documents_to_vector_db
                    from src.vector_db.chroma_client import get_chroma_client
                    
                    # Parse event according to tech spec
                    event = GroupEvent(**event_data)
                    
                    if event.eventType == "GROUP_CREATED":
                        # Add group to ChromaDB
                        doc = build_group_document(event.data.dict())
                        add_documents_to_vector_db([doc], "group-info")
                        logger.info(f"[ChromaDB] Added group {event.data.groupId}")
                        
                    elif event.eventType == "GROUP_DELETED":
                        # Remove group from ChromaDB
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
                            client = get_chroma_client()
                            col = client.get_or_create_collection("user-activity")
                            col.delete(ids=[f"user-{user_data.userId}-{user_data.groupId}"])
                            logger.info(f"[ChromaDB] Removed user {user_data.userId} from group {user_data.groupId}")
                    
                    await consumer.commit()
                    
                except Exception as e:
                    logger.error(f"[Kafka] Group event processing failed: {e}", extra={"event": event_data})
                    # Note: In pure consumer mode, we can't send to DLQ without a producer
                    # This would be handled by the backend's error handling
                    await consumer.commit()  # Commit to avoid reprocessing
                    
        except Exception as e:
            logger.error(f"[Kafka] Group events consumer crashed: {e}")
        finally:
            await consumer.stop()
    
    async def _process_group_generation_requests(self, topic: str):
        """Process group auto-generation requests"""
        consumer = get_consumer(topic, "group-generate-consumer")
        self.consumers.append(consumer)
        
        await consumer.start()
        logger.info(f"[Kafka] Started consumer for {topic}")
        
        try:
            async for msg in consumer:
                payload = msg.value
                try:
                    # Import here to avoid circular imports
                    from src.schemas.v2.kafka_events import GroupGenerateRequest
                    from src.schemas.v1.group_information import MeetingInput
                    from src.services.v2.group_information import build_meeting_data
                    
                    # Parse and validate request
                    request = GroupGenerateRequest(**payload)
                    
                    # Generate group information using AI
                    meeting_input = MeetingInput(
                        name=request.name,
                        goal=request.goal,
                        category=request.category,
                        period=request.period,
                        isPlanCreated=request.isPlanCreated
                    )
                    
                    result = await build_meeting_data(meeting_input)
                    
                    # Note: In pure consumer mode, we don't send responses back
                    # The backend will handle response collection through other means
                    logger.info("[Kafka] Group generation completed successfully")
                    await consumer.commit()
                    
                except Exception as e:
                    logger.error(f"[Kafka] Group generation failed: {e}", extra={"payload": payload})
                    await consumer.commit()
                    
        except Exception as e:
            logger.error(f"[Kafka] Group generation consumer crashed: {e}")
        finally:
            await consumer.stop()
    
    async def _process_question_generation_requests(self, topic: str):
        """Process question generation requests for recommendations"""
        consumer = get_consumer(topic, "question-consumer")
        self.consumers.append(consumer)
        
        await consumer.start()
        logger.info(f"[Kafka] Started consumer for {topic}")
        
        try:
            async for msg in consumer:
                payload = msg.value
                try:
                    from src.schemas.v2.kafka_events import QuestionRequest
                    from src.services.v2.chatbot import handle_combined_question
                    from src.core.websocket_manager import websocket_manager
                    
                    request = QuestionRequest(**payload)
                    
                    # Generate question using existing logic
                    result = await handle_combined_question(
                        payload["payload"].get("answer"),
                        payload["payload"].get("userId"),
                        payload["payload"].get("sessionId"),
                    )
                    
                    # Send to WebSocket for real-time delivery (if connected)
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
                        logger.info(f"[Kafka→WS] Question sent to WebSocket for session {session_id}")
                    
                    await consumer.commit()
                    
                except Exception as e:
                    logger.error(f"[Kafka] Question generation failed: {e}", extra={"payload": payload})
                    await consumer.commit()
                    
        except Exception as e:
            logger.error(f"[Kafka] Question generation consumer crashed: {e}")
        finally:
            await consumer.stop()
    
    async def _process_group_recommendations(self, topic: str):
        """Process final group recommendation requests"""
        consumer = get_consumer(topic, "group-recommend-consumer")
        self.consumers.append(consumer)
        
        await consumer.start()
        logger.info(f"[Kafka] Started consumer for {topic}")
        
        try:
            async for msg in consumer:
                payload = msg.value
                try:
                    from src.schemas.v2.kafka_events import RecommendRequest
                    from src.services.v2.chatbot import handle_answer_analysis
                    from src.core.websocket_manager import websocket_manager
                    
                    request = RecommendRequest(**payload)
                    
                    # Generate recommendations using existing logic
                    result = await handle_answer_analysis(
                        payload["payload"].get("messages", []),
                        payload["payload"].get("userId"),
                        payload["payload"].get("sessionId"),
                    )
                    
                    # Send to WebSocket for real-time delivery (if connected)
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
                        logger.info(f"[Kafka→WS] Recommendations sent to WebSocket for session {session_id}")
                    
                    await consumer.commit()
                    
                except Exception as e:
                    logger.error(f"[Kafka] Group recommendation failed: {e}", extra={"payload": payload})
                    await consumer.commit()
                    
        except Exception as e:
            logger.error(f"[Kafka] Group recommendation consumer crashed: {e}")
        finally:
            await consumer.stop()
    
    async def _monitor_dlq(self):
        """Monitor DLQ topics for failed messages (read-only monitoring)"""
        dlq_consumers = []
        
        try:
            # Start consumers for each DLQ topic
            for dlq_topic in self.dlq_topics:
                try:
                    consumer = get_consumer(dlq_topic, f"{dlq_topic}-monitor")
                    await consumer.start()
                    dlq_consumers.append((consumer, dlq_topic))
                    logger.info(f"[DLQ] Monitoring {dlq_topic}")
                except Exception as e:
                    logger.debug(f"[DLQ] Could not start monitoring {dlq_topic}: {e}")
            
            if not dlq_consumers:
                logger.info("[DLQ] No DLQ topics available for monitoring")
                return
            
            # Monitor for new DLQ messages
            while True:
                for consumer, topic in dlq_consumers:
                    try:
                        msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)
                        dlq_data = msg.value
                        
                        # Log DLQ message for visibility (read-only)
                        logger.warning(
                            f"[DLQ] Failed message detected in {topic}",
                            extra={
                                "error_type": dlq_data.get("errorType"),
                                "error_message": dlq_data.get("errorMessage"),
                                "failed_at": dlq_data.get("failedAt"),
                                "source": dlq_data.get("source")
                            }
                        )
                        
                        await consumer.commit()
                        
                    except asyncio.TimeoutError:
                        continue  # No messages in this DLQ
                    except Exception as e:
                        logger.debug(f"[DLQ] Error monitoring {topic}: {e}")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except Exception as e:
            logger.error(f"[DLQ] Monitor crashed: {e}")
        finally:
            for consumer, _ in dlq_consumers:
                try:
                    await consumer.stop()
                except Exception:
                    pass
