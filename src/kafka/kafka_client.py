import json
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from src.config import KAFKA_BOOTSTRAP_SERVER


def get_producer(bootstrap_servers: str | None = None) -> AIOKafkaProducer:
    return AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers or KAFKA_BOOTSTRAP_SERVER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
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
    )