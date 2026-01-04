import json
from kafka import KafkaProducer
from datetime import datetime
from src.config.loader import config
from src.common.utils import get_logger

logger = get_logger(__name__)

class DLQProducer:
    def __init__(self):
        """
        Initializes the Dead Letter Queue Producer.
        Targeting 'document_tasks_failed' topic for enterprise fault tolerance.
        """
        self.topic = "document_tasks_failed"
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=config.kafka_broker,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',  # Ensure failure logs are physically written to disk
                retries=3
            )
            logger.info(f"🛡️  DLQ Producer active on topic: {self.topic}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize DLQ Producer: {e}")
            self.producer = None

    def publish_failure(self, original_task, error_message, node_id="enricher_alpha"):
        """
        Wraps the failed task with diagnostic metadata and sends to DLQ.
        """
        if not self.producer:
            logger.error("🛑 DLQ Producer unavailable. Failure message lost!")
            return

        failed_payload = {
            "original_task": original_task,
            "failure_context": {
                "node_id": node_id,
                "error": str(error_message),
                "timestamp": datetime.now().isoformat(),
                "attempt": original_task.get("retry_count", 0) + 1
            },
            "status": "DLQ_PENDING"
        }

        try:
            self.producer.send(self.topic, failed_payload)
            self.producer.flush()
            logger.warning(f"📥 Task {original_task.get('id')} moved to DLQ: {error_message}")
        except Exception as e:
            logger.error(f"❌ Critical failure while writing to DLQ: {e}")

    def close(self):
        if self.producer:
            self.producer.close()