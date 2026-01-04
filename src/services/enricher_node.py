import json
from kafka import KafkaConsumer, KafkaProducer
from src.agents.intelligence.ocr_engine import ProcessingWorker
from src.config.loader import config
from src.common.utils import get_logger
from src.common.dlq_producer import DLQProducer
from src.common.monitor import EnterpriseMonitor

logger = get_logger(__name__)

def run_enricher():
    """
    Enterprise Enricher Node with DLQ and Audit Monitoring.
    """
    # 1. Initialize Engines and Monitoring
    worker = ProcessingWorker()
    dlq = DLQProducer()
    monitor = EnterpriseMonitor()

    # 2. Setup Kafka Consumer (Input Queue)
    consumer = KafkaConsumer(
        'document_tasks',
        bootstrap_servers=config.kafka_broker,
        group_id='enterprise_enricher_group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest'
    )

    # 3. Setup Kafka Producer (Output Queue)
    producer = KafkaProducer(
        bootstrap_servers=config.kafka_broker,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    logger.info("🚀 Enricher Service Online. Listening for tasks...")

    for message in consumer:
        task = message.value
        filename = task.get('filename', 'Unknown')

        try:
            logger.info(f"📥 Processing: {filename}")

            # Heavy Lift: OCR and Embeddings
            result = worker.process_message(task)

            if result:
                # Success path
                producer.send('document_results', result)
                producer.flush()
                monitor.log_event(task, "SUCCESS", "enricher")
                logger.info(f"✅ Enrichment Complete: {filename} sent to Sink.")
            else:
                # Logic failure (e.g., unsupported format)
                error_msg = "Enrichment returned empty result"
                dlq.publish_failure(task, error_msg)
                monitor.log_event(task, "FAILED", "enricher", error_msg)

        except Exception as e:
            # System failure
            logger.error(f"❌ AI Processing Failure for {filename}: {e}")
            dlq.publish_failure(task, str(e))
            monitor.log_event(task, "FAILED", "enricher", str(e))

    # Clean up
    dlq.close()

if __name__ == "__main__":
    run_enricher()