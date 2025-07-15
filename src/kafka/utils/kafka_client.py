import json
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from src.config import KAFKA_BOOTSTRAP_SERVER

# Completely suppress all Kafka-related logging to prevent spam
loggers_to_suppress = [
    'aiokafka', 'aiokafka.consumer', 'aiokafka.producer', 'aiokafka.client',
    'aiokafka.cluster', 'aiokafka.coordinator', 'aiokafka.coordinator.consumer',
    'aiokafka.coordinator.group', 'aiokafka.coordinator.assignors',
    'kafka', 'kafka.cluster', 'kafka.protocol', 'kafka.consumer', 
    'kafka.producer', 'kafka.coordinator', 'kafka.client'
]

for logger_name in loggers_to_suppress:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL + 1)

def get_producer(bootstrap_servers: str | None = None) -> AIOKafkaProducer:
    return AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers or KAFKA_BOOTSTRAP_SERVER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        # Add connection timeout and retry settings
        request_timeout_ms=2000,         # 2 second timeout (reduced)
        retry_backoff_ms=100,            # 100ms between retries
        max_in_flight_requests_per_connection=1,
        retries=1,                       # Reduce retries to minimize delay
    )


def get_consumer(
    topic: str,
    group_id: str,
    bootstrap_servers: str | None = None,
) -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers or KAFKA_BOOTSTRAP_SERVER,
        group_id=group_id,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        # Add aggressive connection timeout and session settings
        request_timeout_ms=2000,         # 2 second timeout (reduced)
        session_timeout_ms=3000,         # 3 second session timeout (reduced)
        heartbeat_interval_ms=1000,      # 1 second heartbeat (reduced)
        max_poll_interval_ms=5000,       # 5 second max poll interval (reduced)
        retry_backoff_ms=100,            # 100ms between retries
        metadata_max_age_ms=5000,        # 5 second metadata cache (reduced)
        connections_max_idle_ms=5000,    # 5 second idle connection timeout (reduced)
    )
