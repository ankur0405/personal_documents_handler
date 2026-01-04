import json
import time
import lancedb
import pyarrow as pa
from kafka import KafkaConsumer
from src.config.loader import config
from src.common.utils import get_logger
from src.common.dlq_producer import DLQProducer
from src.common.monitor import EnterpriseMonitor

logger = get_logger(__name__)

def get_schema():
    return pa.schema([
        pa.field("id", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), config.model_dimension)),
        pa.field("filename", pa.string()),
        pa.field("file_path", pa.string()),
        pa.field("file_type", pa.string()),
        pa.field("content", pa.string(), nullable=True),
        pa.field("tags", pa.list_(pa.string())),
        pa.field("source", pa.string()),
        pa.field("engine_version", pa.string()),
        pa.field("timestamp", pa.string()),
        pa.field("created_at", pa.string()),
        pa.field("category", pa.string()),
        pa.field("processing_status", pa.string()),
        pa.field("page_number", pa.int32()),
        pa.field("last_modified", pa.float64()),
        pa.field("issue_date", pa.string()),
        pa.field("expiry_date", pa.string()),
        pa.field("primary_date", pa.string()),
        pa.field("country", pa.string()),
        pa.field("person", pa.string())
    ])

def run_sink():
    # 1. Initialize DB and Monitoring
    db = lancedb.connect(config.db_path)
    monitor = EnterpriseMonitor()
    dlq = DLQProducer()
    table_name = "document_intel"
    
    if table_name not in db.list_tables():
        table = db.create_table(table_name, schema=get_schema())
    else:
        table = db.open_table(table_name)

    # 2. Kafka Consumer
    consumer = KafkaConsumer(
        'document_results',
        bootstrap_servers=config.kafka_broker,
        group_id='enterprise_sink_group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True
    )

    logger.info(f"📥 Singleton Sink Active. Monitoring 'document_results'")

    last_index_time = time.time()
    pending_count = 0
    INDEX_THRESHOLD_DOCS = 10 
    INDEX_THRESHOLD_TIME = 300 

    for message in consumer:
        result = message.value
        filename = result.get('filename', 'Unknown')
        
        # Format task for monitor logging
        task_meta = {"id": result.get("id"), "filename": filename}

        try:
            # 4. Atomic Write
            table.add([result])
            monitor.log_event(task_meta, "SUCCESS", "sink")
            logger.info(f"💾 Database Commit: {filename}")
            
            pending_count += 1
            current_time = time.time()

            # 5. FTS Maintenance
            if pending_count >= INDEX_THRESHOLD_DOCS or (current_time - last_index_time) > INDEX_THRESHOLD_TIME:
                table.create_fts_index("content", replace=True)
                logger.info("✅ FTS Index Optimized.")
                pending_count = 0
                last_index_time = current_time

        except Exception as e:
            # Storage failure: Send back to DLQ for retry
            logger.error(f"❌ Failed to commit {filename} to DB: {e}")
            dlq.publish_failure(result, f"SINK_ERROR: {str(e)}", node_id="sink_node")
            monitor.log_event(task_meta, "FAILED", "sink", str(e))

if __name__ == "__main__":
    run_sink()