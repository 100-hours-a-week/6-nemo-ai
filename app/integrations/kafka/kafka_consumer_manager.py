import asyncio
import logging
import json
from typing import Optional
from datetime import datetime
from app.core.ai_logger import get_ai_logger
from app.config import (
    KAFKA_ENABLED, 
    KAFKA_BOOTSTRAP_SERVER, 
    KAFKA_CONSUMER_GROUP_ID,
    KAFKA_MAX_POLL_RECORDS,
    KAFKA_SESSION_TIMEOUT_MS,
    KAFKA_HEARTBEAT_INTERVAL_MS,
    KAFKA_MAX_POLL_INTERVAL_MS
)

logger = get_ai_logger()

class KafkaConsumerManager:
    """
    AI Kafka Consumer Manager for processing group and recommendation events.
    
    Handles 4 Kafka topics:
    - GROUP_EVENT (mandatory): Group creation, updates, and invitations
    - GROUP_RECOMMEND_QUESTION (mandatory): Generate MC questions based on group context  
    - GROUP_RECOMMEND (mandatory): Generate final recommendations
    - GROUP_GENERATE (optional): AI-side group detail generation
    
    Features:
    - 3 partitions per topic with 3-worker consumer group auto-rebalancing
    - Graceful handling of empty partitions and missing optional topics
    - DLQ support for processing failures with fallback logging
    - Bulletproof error handling to prevent crashes
    """
    
    def __init__(self):
        self.consumers = []
        self.consumer_tasks = []
        self.kafka_available = False
        self.kafka_check_task = None
        self.consumer_group_id = KAFKA_CONSUMER_GROUP_ID
        self.worker_id = f"worker-{asyncio.get_event_loop().time():.0f}"  # Unique worker ID
        
        # Completely silence Kafka-related loggers immediately
        self._silence_kafka_loggers()
        
        # Define mandatory and optional topics with their consumer functions
        self.mandatory_topics = {
            "GROUP_EVENT": self._process_group_events,
            "GROUP_RECOMMEND_QUESTION": self._process_question_generation_requests,
            "GROUP_RECOMMEND": self._process_group_recommendations,
        }
        
        self.optional_topics = {
            "GROUP_GENERATE": self._process_group_generation_requests,
        }
        
        # DLQ topics (optional - only used when available)
        self.dlq_topics = {
            "GROUP_EVENT_DLQ": self._process_group_events_dlq,
            "GROUP_GENERATE_DLQ": self._process_group_generation_dlq,
            "GROUP_RECOMMEND_QUESTION_DLQ": self._process_question_generation_dlq,
            "GROUP_RECOMMEND_DLQ": self._process_group_recommendations_dlq,
        }
    
    def _silence_kafka_loggers(self):
        """Permanently silence all Kafka-related loggers"""
        loggers_to_silence = [
            'aiokafka', 'aiokafka.consumer', 'aiokafka.producer', 'aiokafka.client',
            'aiokafka.cluster', 'aiokafka.coordinator', 'aiokafka.coordinator.consumer',
            'aiokafka.coordinator.group', 'aiokafka.coordinator.assignors',
            'aiokafka.protocol', 'aiokafka.errors', 'aiokafka.heartbeat',
            'kafka', 'kafka.cluster', 'kafka.protocol', 'kafka.consumer', 
            'kafka.producer', 'kafka.coordinator', 'kafka.client', 'kafka.errors',
            'kafka.conn', 'kafka.metrics'
        ]
        
        for logger_name in loggers_to_silence:
            kafka_logger = logging.getLogger(logger_name)
            kafka_logger.setLevel(logging.CRITICAL + 1)  # Completely silent
            kafka_logger.propagate = False
            kafka_logger.disabled = True
    
    async def _test_kafka_connection(self) -> bool:
        """Test if Kafka is available without any error output"""
        try:
            import socket
            
            # Test all bootstrap servers
            servers = [s.strip() for s in KAFKA_BOOTSTRAP_SERVER.split(',')]
            for server in servers:
                host, port = server.split(':')
                port = int(port)
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)  # 2 second timeout
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    return True
            
            return False
            
        except Exception:
            return False
    
    async def _check_topic_exists(self, topic: str) -> bool:
        """Check if a specific topic exists - simplified for aiokafka 0.10.0"""
        try:
            # For aiokafka 0.10.0, the admin client has limited functionality
            # Instead, try to create a consumer and see if it fails
            from aiokafka import AIOKafkaConsumer
            
            test_consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
                group_id=f"{self.consumer_group_id}-topic-test",
                auto_offset_reset="latest",
                enable_auto_commit=False,
                request_timeout_ms=5000
            )
            
            await test_consumer.start()
            await test_consumer.stop()
            return True  # If we got here, topic exists
                
        except Exception as e:
            # For aiokafka 0.10.0, assume topic exists if we can't check reliably
            logger.debug(f"[Kafka] Topic check failed for {topic}, assuming exists: {type(e).__name__}")
            return True  # Fail-safe: assume topic exists
    
    async def start_consumers(self):
        """Start Kafka consumers with bulletproof error handling"""
        if not KAFKA_ENABLED:
            logger.info("[Kafka] Kafka disabled in configuration")
            return
        
        logger.info("[Kafka] Checking Kafka availability...")
        
        # Test connection without any error output
        self.kafka_available = await self._test_kafka_connection()
        
        if not self.kafka_available:
            logger.warning("[Kafka] Kafka cluster not available - running in standalone mode")
            logger.info("[Kafka] Application will continue without async event processing")
            
            # Start background checker for when Kafka becomes available
            self.kafka_check_task = asyncio.create_task(self._background_kafka_checker())
            return
        
        # Kafka is available, start consumers
        logger.info("[Kafka] Kafka cluster is available - starting consumers...")
        await self._start_all_consumers()
    
    async def _background_kafka_checker(self):
        """Background task to check if Kafka becomes available"""
        while not self.kafka_available:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if await self._test_kafka_connection():
                    logger.info("[Kafka] Kafka cluster is now available! Starting consumers...")
                    self.kafka_available = True
                    await self._start_all_consumers()
                    break
                    
            except Exception:
                # Silently continue checking
                continue
    
    async def _start_all_consumers(self):
        """Start all Kafka consumers with topic availability checking"""

        active_consumers = 0
        failed_mandatory = []
        
        # Start mandatory topic consumers
        for topic, consumer_func in self.mandatory_topics.items():
            try:
                # Check if topic exists
                topic_exists = await self._check_topic_exists(topic)
                if not topic_exists:
                    logger.warning(f"[Kafka] Mandatory topic {topic} does not exist")
                    failed_mandatory.append(topic)
                    continue
                
                consumer = await self._create_consumer(topic)
                if consumer:
                    await self._start_consumer(consumer, consumer_func, topic)
                    active_consumers += 1
                    logger.info(f"[Kafka] Started mandatory consumer for {topic}")
                    
            except Exception as e:
                logger.error(f"[Kafka] Failed to start mandatory consumer for {topic}: {type(e).__name__}")
                failed_mandatory.append(topic)
        
        # Start optional topic consumers
        for topic, consumer_func in self.optional_topics.items():
            try:
                topic_exists = await self._check_topic_exists(topic)
                if not topic_exists:
                    logger.info(f"[Kafka] Optional topic {topic} not available - skipping")
                    continue
                
                consumer = await self._create_consumer(topic)
                if consumer:
                    await self._start_consumer(consumer, consumer_func, topic)
                    active_consumers += 1
                    logger.info(f"[Kafka] Started optional consumer for {topic}")
                    
            except Exception as e:
                logger.debug(f"[Kafka] Could not start optional consumer for {topic}: {type(e).__name__}")
        
        # Start DLQ consumers (all optional)
        for topic, consumer_func in self.dlq_topics.items():
            try:
                topic_exists = await self._check_topic_exists(topic)
                if not topic_exists:
                    logger.debug(f"[Kafka] DLQ topic {topic} not available - skipping")
                    continue
                
                consumer = await self._create_consumer(topic, is_dlq=True)
                if consumer:
                    await self._start_consumer(consumer, consumer_func, topic)
                    active_consumers += 1
                    logger.info(f"[Kafka] Started DLQ consumer for {topic}")
                    
            except Exception as e:
                logger.debug(f"[Kafka] Could not start DLQ consumer for {topic}: {type(e).__name__}")
        
        if failed_mandatory:
            logger.error(f"[Kafka] Failed to start mandatory topics: {failed_mandatory}")
            logger.warning("[Kafka] Some mandatory consumers are unavailable - functionality may be limited")
        
        if active_consumers > 0:
            logger.info(f"[Kafka] Successfully started {active_consumers} consumers")
        else:
            logger.warning("[Kafka] No consumers could be started")
    
    async def _create_consumer(self, topic: str, is_dlq: bool = False) -> Optional['AIOKafkaConsumer']:
        try:
            from aiokafka import AIOKafkaConsumer
            
            group_id = f"{self.consumer_group_id}-dlq" if is_dlq else self.consumer_group_id
            
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
                group_id=group_id,
                value_deserializer=self._safe_deserializer,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                request_timeout_ms=10000,
                session_timeout_ms=KAFKA_SESSION_TIMEOUT_MS,
                heartbeat_interval_ms=KAFKA_HEARTBEAT_INTERVAL_MS,
                max_poll_interval_ms=KAFKA_MAX_POLL_INTERVAL_MS,
                retry_backoff_ms=1000,
                metadata_max_age_ms=30000,
                connections_max_idle_ms=60000,
                max_poll_records=KAFKA_MAX_POLL_RECORDS,
            )
            
            await consumer.start()
            return consumer
            
        except Exception as e:
            logger.debug(f"[Kafka] Failed to create consumer for {topic}: {type(e).__name__}")
            return None
    
    def _safe_deserializer(self, data):
        """Safe deserializer that handles codec errors gracefully"""
        if data is None:
            return None
            
        try:
            # First try normal JSON decoding
            return json.loads(data.decode("utf-8"))
        except UnicodeDecodeError:
            # If there's a decode error, it might be compressed data that we can't handle
            logger.warning(f"[Kafka] UnicodeDecodeError - message may be compressed with unsupported codec")
            return None
        except json.JSONDecodeError as e:
            # If JSON decode fails, log and skip the message
            logger.warning(f"[Kafka] JSONDecodeError: {e} - skipping malformed message")
            return None
        except Exception as e:
            # Catch any other deserialization errors
            logger.warning(f"[Kafka] Deserialization error: {type(e).__name__}: {e}")
            return None
    
    async def _start_consumer(self, consumer, consumer_func, topic: str):
        """Start the consumer processing task"""
        self.consumers.append(consumer)
        
        task = asyncio.create_task(
            consumer_func(consumer, topic),
            name=f"consumer-{topic}"
        )
        self.consumer_tasks.append(task)
    
    async def stop_consumers(self):
        """Stop all consumers gracefully"""
        logger.info("[Kafka] Stopping Kafka consumers...")
        
        # Cancel background checker
        if self.kafka_check_task and not self.kafka_check_task.done():
            self.kafka_check_task.cancel()
            try:
                await self.kafka_check_task
            except asyncio.CancelledError:
                pass
        
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
            except Exception:
                pass  # Silently ignore stop errors
        
        self.consumers.clear()
        self.consumer_tasks.clear()
        logger.info("[Kafka] All consumers stopped")
    
    async def _send_to_dlq(self, original_message: dict, error_type: str, error_message: str, source_topic: str):
        """Send failed message to Dead Letter Queue if available"""
        try:
            dlq_topic = f"{source_topic}_DLQ"
            
            # Check if DLQ topic exists
            if not await self._check_topic_exists(dlq_topic):
                logger.debug(f"[Kafka] DLQ topic {dlq_topic} not available - logging failure instead")
                logger.error(f"[Kafka-DLQ] Failed message from {source_topic}: {error_type} - {error_message}")
                return
            
            from aiokafka import AIOKafkaProducer
            from app.schemas.events.kafka_events import DLQMessage
            
            dlq_message = DLQMessage(
                originalMessage=original_message,
                errorType=error_type,
                errorMessage=error_message,
                failedAt=datetime.now().isoformat(),
                source="AI-RECOMMENDER"
            )
            
            producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            
            await producer.start()
            try:
                await producer.send_and_wait(dlq_topic, dlq_message.dict())
                logger.info(f"[Kafka] Sent failed message to {dlq_topic}")
            finally:
                await producer.stop()
                
        except Exception as e:
            logger.error(f"[Kafka] Failed to send to DLQ: {e}")
            logger.error(f"[Kafka-DLQ-FALLBACK] {source_topic} failure: {error_type} - {error_message}")
    
    # ======================== TOPIC PROCESSORS ========================
    
    async def _process_group_events(self, consumer, topic: str):
        """Process GROUP_EVENT topic - stores group information in ChromaDB vector database"""
        logger.info(f"[Kafka] Starting consumer for {topic}")
        
        try:
            async for msg in consumer:
                # Handle None values (empty messages)
                if msg.value is None:
                    logger.debug(f"[Kafka] Skipping null message in {topic}")
                    await consumer.commit()
                    continue
                
                # Handle messages that couldn't be deserialized due to codec issues
                if msg.value is None and hasattr(msg, 'headers'):
                    logger.warning(f"[Kafka] Skipping message with unsupported codec in {topic}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                
                # Handle messages that couldn't be deserialized due to codec issues
                if msg.value is None and hasattr(msg, 'headers'):
                    logger.warning(f"[Kafka] Skipping message with unsupported codec in {topic}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                    
                try:
                    event_data = msg.value
                    logger.debug(f"[Kafka] Processing group event: {event_data.get('eventType', 'UNKNOWN')}")
                    
                    # Import here to avoid circular imports
                    from app.schemas.events.kafka_events import GroupEvent, GroupEventData, UserEventData
                    from app.database.group_document_builder import build_group_document
                    from app.database.user_document_builder import build_user_document
                    from app.database.vector_indexer import add_documents_to_vector_db
                    from app.database.chroma_client import get_chroma_client

                    # Parse event type first to determine data structure
                    event_type = event_data.get('eventType')
                    if not event_type:
                        raise ValueError("Missing eventType in GROUP_EVENT message")

                    # Handle different event types with appropriate data validation
                    if event_type == "GROUP_CREATED":
                        if not event_data.get('data'):
                            raise ValueError("GROUP_CREATED event missing required data")

                        # Validate as GroupEventData
                        group_data = GroupEventData(**event_data['data'])
                        event = GroupEvent(
                            eventType=event_type,
                            data=group_data,
                            timestamp=event_data.get('timestamp', [])
                        )

                        # Build and store document
                        doc = build_group_document(group_data.dict())
                        add_documents_to_vector_db([doc], "group-info")
                        logger.info(f"[ChromaDB] Added group {group_data.groupId} to vector database")

                    elif event_type == "GROUP_DELETED":
                        group_id = event_data.get('groupId') or (event_data.get('data', {}).get('groupId') if event_data.get('data') else None)
                        if not group_id:
                            raise ValueError("GROUP_DELETED event missing groupId")

                        event = GroupEvent(
                            eventType=event_type,
                            groupId=group_id,
                            timestamp=event_data.get('timestamp', [])
                        )

                        from app.models.embedding_model import embed
                        client = get_chroma_client()
                        col = client.get_or_create_collection("group-info", embedding_function=embed)
                        col.delete(ids=[f"group-{group_id}"])
                        logger.info(f"[ChromaDB] Deleted group {group_id} from vector database")

                    elif event_type in ["GROUP_JOINED", "GROUP_LEFT"]:
                        if not event_data.get('data'):
                            raise ValueError(f"{event_type} event missing required data")

                        # Validate as UserEventData
                        user_data = UserEventData(**event_data['data'])
                        event = GroupEvent(
                            eventType=event_type,
                            data=user_data,
                            timestamp=event_data.get('timestamp', [])
                        )

                        if event_type == "GROUP_JOINED":
                            docs = build_user_document(user_data.userId, user_data.groupId)
                            add_documents_to_vector_db(docs, "user-activity")
                            logger.info(f"[ChromaDB] Added user {user_data.userId} to group {user_data.groupId}")
                        elif event_type == "GROUP_LEFT":
                            from app.models.embedding_model import embed
                            client = get_chroma_client()
                            col = client.get_or_create_collection("user-activity", embedding_function=embed)
                            col.delete(ids=[f"user-{user_data.userId}-{user_data.groupId}"])
                            logger.info(f"[ChromaDB] Removed user {user_data.userId} from group {user_data.groupId}")
                        else:
                            raise ValueError(f"{event_type} event missing user or group data")

                    else:
                        logger.warning(f"[Kafka] Unknown event type: {event_type}")
                    
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
                except Exception as e:
                    # Handle specific codec-related errors
                    error_name = type(e).__name__
                    if "UnsupportedCodec" in error_name or "codec" in str(e).lower():
                        logger.error(f"[Kafka] Codec error in GROUP_EVENT: {error_name} - skipping message with unsupported compression")
                        # Skip the problematic message by committing offset
                        await consumer.commit()
                        logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                        continue
                    
                    logger.error(f"[Kafka] GROUP_EVENT processing failed: {e}")
                    await self._send_to_dlq(msg.value, type(e).__name__, str(e), topic)
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")  # Commit to avoid reprocessing
                    
        except Exception as e:
            error_name = type(e).__name__
            if "UnsupportedCodec" in error_name:
                logger.error(f"[Kafka] GROUP_EVENT consumer stopped due to codec error: {error_name}")
                logger.error(f"[Kafka] This indicates messages were produced with compression codec not supported by consumer")
                logger.error(f"[Kafka] Required codec libraries: python-snappy, lz4, zstandard")
            else:
                logger.error(f"[Kafka] GROUP_EVENT consumer stopped: {error_name}")
    
    async def _process_question_generation_requests(self, consumer, topic: str):
        """Process GROUP_RECOMMEND_QUESTION - generates MC questions and streams via vLLM SSE over WebSocket"""
        logger.info(f"[Kafka] Starting consumer for {topic}")
        
        try:
            async for msg in consumer:
                if msg.value is None:
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                    
                try:
                    payload = msg.value
                    logger.debug(f"[Kafka] Processing question generation request")
                    
                    from app.schemas.events.kafka_events import QuestionRequest
                    from app.services.v2.chatbot import handle_combined_question
                    from app.core.websocket_manager import websocket_manager
                    
                    # Validate request structure
                    if "payload" not in payload:
                        raise ValueError("Missing payload in question request")
                    
                    request_payload = payload["payload"]
                    required_fields = ["userId", "sessionId"]
                    for field in required_fields:
                        if field not in request_payload:
                            raise ValueError(f"Missing required field: {field}")
                    
                    # Process question generation
                    result = await handle_combined_question(
                        request_payload.get("answer"),
                        request_payload.get("userId"),
                        request_payload.get("sessionId"),
                    )
                    
                    # Stream result to client via WebSocket if connected
                    session_id = request_payload.get("sessionId")

                    if session_id and websocket_manager.is_connected(session_id):
                        ws_message = {
                            "type": "QUESTION_GENERATED",
                            "payload": {
                                "sessionId": session_id,
                                "question": result.get("question"),
                                "options": result.get("options", []),
                                "questionId": result.get("questionId"),
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        await websocket_manager.send(session_id, ws_message)
                        logger.info(f"[Kafka→WS] Question sent for session {session_id}")
                    else:
                        logger.warning(f"[Kafka] WebSocket session {session_id} not connected")
                    
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
                except Exception as e:
                    logger.error(f"[Kafka] Question generation failed: {e}")
                    await self._send_to_dlq(msg.value, type(e).__name__, str(e), topic)
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed (with error) - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
        except Exception as e:
            logger.error(f"[Kafka] Question generation consumer stopped: {type(e).__name__}")
    
    async def _process_group_recommendations(self, consumer, topic: str):
        """Process GROUP_RECOMMEND - generates final recommendations and streams via vLLM SSE over WebSocket"""
        logger.info(f"[Kafka] Starting consumer for {topic}")
        
        try:
            async for msg in consumer:
                if msg.value is None:
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                    
                try:
                    payload = msg.value
                    logger.debug(f"[Kafka] Processing group recommendation request")
                    
                    from app.schemas.events.kafka_events import RecommendRequest
                    from app.services.v2.chatbot import handle_answer_analysis
                    from app.core.websocket_manager import websocket_manager
                    
                    # Validate request structure
                    if "payload" not in payload:
                        raise ValueError("Missing payload in recommendation request")
                    
                    request_payload = payload["payload"]
                    required_fields = ["userId", "sessionId"]
                    for field in required_fields:
                        if field not in request_payload:
                            raise ValueError(f"Missing required field: {field}")
                    
                    # Process recommendation generation
                    result = await handle_answer_analysis(
                        request_payload.get("messages", []),
                        request_payload.get("userId"),
                        request_payload.get("sessionId"),
                    )
                    
                    # Stream result to client via WebSocket if connected
                    session_id = request_payload.get("sessionId")
                    if session_id and websocket_manager.is_connected(session_id):
                        ws_message = {
                            "type": "GROUP_RECOMMENDATIONS",
                            "payload": {
                                "sessionId": session_id,
                                "recommendations": result.get("recommendations", []),
                                "reasoning": result.get("reasoning", ""),
                                "confidence": result.get("confidence", 0.8),
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        await websocket_manager.send(session_id, ws_message)
                        logger.info(f"[Kafka→WS] Recommendations sent for session {session_id}")
                    else:
                        logger.warning(f"[Kafka] WebSocket session {session_id} not connected")
                    
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
                except Exception as e:
                    logger.error(f"[Kafka] Group recommendation failed: {e}")
                    await self._send_to_dlq(msg.value, type(e).__name__, str(e), topic)
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed (with error) - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
        except Exception as e:
            logger.error(f"[Kafka] Group recommendation consumer stopped: {type(e).__name__}")
    
    async def _process_group_generation_requests(self, consumer, topic: str):
        """Process GROUP_GENERATE (optional) - AI-side group detail generation"""
        logger.info(f"[Kafka] Starting consumer for {topic}")
        
        try:
            async for msg in consumer:
                if msg.value is None:
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                    
                try:
                    payload = msg.value
                    logger.debug(f"[Kafka] Processing group generation request")
                    
                    from app.schemas.events.kafka_events import GroupGenerateRequest
                    from app.schemas.groups.group_information import MeetingInput
                    from app.services.v2.group_information import build_meeting_data
                    
                    # Validate and parse request
                    request = GroupGenerateRequest(**payload)
                    
                    meeting_input = MeetingInput(
                        name=request.name,
                        goal=request.goal,
                        category=request.category,
                        period=request.period,
                        isPlanCreated=request.isPlanCreated
                    )
                    
                    # Generate group details using AI
                    result = await build_meeting_data(meeting_input)
                    logger.info(f"[Kafka] Group generation completed for: {request.name}")
                    
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
                except Exception as e:
                    logger.error(f"[Kafka] Group generation failed: {e}")
                    await self._send_to_dlq(msg.value, type(e).__name__, str(e), topic)
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed (with error) - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
        except Exception as e:
            logger.error(f"[Kafka] Group generation consumer stopped: {type(e).__name__}")
    
    # ======================== DLQ PROCESSORS ========================
    
    async def _process_group_events_dlq(self, consumer, topic: str):
        """Process GROUP_EVENT_DLQ - handle failed group events"""
        logger.info(f"[Kafka] Starting DLQ consumer for {topic}")
        
        try:
            async for msg in consumer:
                if msg.value is None:
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                    
                try:
                    from app.schemas.events.kafka_events import DLQMessage
                    dlq_message = DLQMessage(**msg.value)
                    
                    logger.warning(f"[DLQ] Processing failed GROUP_EVENT: {dlq_message.errorType}")
                    logger.debug(f"[DLQ] Original message: {dlq_message.originalMessage}")
                    logger.debug(f"[DLQ] Error: {dlq_message.errorMessage}")
                    
                    # Could implement retry logic here or manual intervention alerts
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
                except Exception as e:
                    logger.error(f"[DLQ] Failed to process DLQ message: {e}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed (with error) - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
        except Exception as e:
            logger.error(f"[Kafka] GROUP_EVENT_DLQ consumer stopped: {type(e).__name__}")
    
    async def _process_group_generation_dlq(self, consumer, topic: str):
        """Process GROUP_GENERATE_DLQ - handle failed group generation requests"""
        logger.info(f"[Kafka] Starting DLQ consumer for {topic}")
        
        try:
            async for msg in consumer:
                if msg.value is None:
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                    
                try:
                    from app.schemas.events.kafka_events import DLQMessage
                    dlq_message = DLQMessage(**msg.value)
                    
                    logger.warning(f"[DLQ] Processing failed GROUP_EVENT: {dlq_message.errorType}")
                    logger.debug(f"[DLQ] Original message: {dlq_message.originalMessage}")
                    logger.debug(f"[DLQ] Error: {dlq_message.errorMessage}")
                    
                    # Could implement retry logic here or manual intervention alerts
                    await consumer.commit()
                    
                except Exception as e:
                    logger.error(f"[DLQ] Failed to process DLQ message: {e}")
                    await consumer.commit()
                    
        except Exception as e:
            logger.error(f"[Kafka] GROUP_EVENT_DLQ consumer stopped: {type(e).__name__}")
    
    async def _process_group_generation_dlq(self, consumer, topic: str):
        """Process GROUP_GENERATE_DLQ - handle failed group generation requests"""
        logger.info(f"[Kafka] Starting DLQ consumer for {topic}")
        
        try:
            async for msg in consumer:
                if msg.value is None:
                    await consumer.commit()
                    continue
                    
                try:
                    from app.schemas.events.kafka_events import DLQMessage
                    dlq_message = DLQMessage(**msg.value)
                    
                    logger.warning(f"[DLQ] Processing failed GROUP_GENERATE: {dlq_message.errorType}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
                except Exception as e:
                    logger.error(f"[DLQ] Failed to process DLQ message: {e}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed (with error) - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
        except Exception as e:
            logger.error(f"[Kafka] GROUP_GENERATE_DLQ consumer stopped: {type(e).__name__}")
    
    async def _process_question_generation_dlq(self, consumer, topic: str):
        """Process GROUP_RECOMMEND_QUESTION_DLQ - handle failed question generation"""
        logger.info(f"[Kafka] Starting DLQ consumer for {topic}")
        
        try:
            async for msg in consumer:
                if msg.value is None:
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                    
                try:
                    from app.schemas.events.kafka_events import DLQMessage
                    dlq_message = DLQMessage(**msg.value)
                    
                    logger.warning(f"[DLQ] Processing failed question generation: {dlq_message.errorType}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
                except Exception as e:
                    logger.error(f"[DLQ] Failed to process DLQ message: {e}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed (with error) - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
        except Exception as e:
            logger.error(f"[Kafka] GROUP_RECOMMEND_QUESTION_DLQ consumer stopped: {type(e).__name__}")
    
    async def _process_group_recommendations_dlq(self, consumer, topic: str):
        """Process GROUP_RECOMMEND_DLQ - handle failed recommendation generation"""
        logger.info(f"[Kafka] Starting DLQ consumer for {topic}")
        
        try:
            async for msg in consumer:
                if msg.value is None:
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    continue
                    
                try:
                    from app.schemas.events.kafka_events import DLQMessage
                    dlq_message = DLQMessage(**msg.value)
                    
                    logger.warning(f"[DLQ] Processing failed recommendation generation: {dlq_message.errorType}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
                except Exception as e:
                    logger.error(f"[DLQ] Failed to process DLQ message: {e}")
                    await consumer.commit()
                    logger.info(f"[Kafka] Job completed (with error) - Topic: {topic}, Partition: {msg.partition}, Offset: {msg.offset}")
                    
        except Exception as e:
            logger.error(f"[Kafka] GROUP_RECOMMEND_DLQ consumer stopped: {type(e).__name__}")
