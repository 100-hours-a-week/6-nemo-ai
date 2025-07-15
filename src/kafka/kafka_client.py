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
        # Production-ready settings for aiokafka 0.10.0
        request_timeout_ms=30000,        # 30 second timeout for production
        compression_type='gzip',         # Enable compression
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
        request_timeout_ms=30000,        # 30 second timeout
        session_timeout_ms=60000,        # 60 second session timeout
        heartbeat_interval_ms=20000,     # 20 second heartbeat
        max_poll_interval_ms=300000,     # 5 minute max poll interval
        fetch_max_wait_ms=1000,          # Max wait for fetch
        fetch_min_bytes=1,               # Min bytes to fetch
        fetch_max_bytes=52428800,        # 50MB max fetch size
    )
