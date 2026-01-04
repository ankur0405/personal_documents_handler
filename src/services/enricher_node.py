import json
import os
from kafka import KafkaConsumer, KafkaProducer
from src.agents.embedding_agent.worker import ProcessingWorker
from src.config.loader import config
from src.common.utils import get_logger

logger = get_logger(__name__)

def run_worker_node():
    """
    Enterprise Enricher Node:
    - Consumes 'document_tasks' (What to do)
    - Performs OCR & GPU Embeddings
    - Publishes to 'document_results' (The finished data)
    """
    # 1. Initialize the AI Engine (PaddleOCR + SentenceTransformer)
    worker = ProcessingWorker()
    
    # 2. Setup Kafka Consumer (Input Queue)
    consumer = KafkaConsumer(
        'document_tasks',
        bootstrap_servers=config.kafka_broker,
        group_id='enterprise_worker_group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest'
    )

    # 3. Setup Kafka Producer (Output Queue to Sink)
    producer = KafkaProducer(
        bootstrap_servers=config.kafka_broker,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    logger.info("🚀 Worker Node (Enricher) active. Waiting for AI tasks...")

    for message in consumer:
        task = message.value
        filename = task.get('filename')
        
        try:
            logger.info(f"🧠 AI Processing: {filename}")
            
            # Heavy Lift: OCR and Embeddings happen here
            # This is where your 64GB Mac / GPU is utilized
            processed_records = worker.process_message(task)
            
            if processed_records:
                for record in processed_records:
                    # Offload the result to Kafka. The Worker doesn't wait for the DB!
                    producer.send('document_results', record)
                
                producer.flush()
                logger.info(f"✅ Enrichment Complete: {filename} sent to Sink.")
            
        except Exception as e:
            logger.error(f"❌ AI Processing Failure for {filename}: {e}")

if __name__ == "__main__":
    run_worker_node()