import json
from kafka import KafkaConsumer
from src.common.db import DatabaseManager
from src.common.utils import get_logger

logger = get_logger(__name__)

def run_db_sink():
    db_manager = DatabaseManager()
    table = db_manager.initialize_table()
    
    # Get the valid column names from the current table schema
    valid_fields = set(table.schema.names)
    logger.info(f"📋 Valid Schema Fields: {valid_fields}")

    consumer = KafkaConsumer(
        'document_results',
        bootstrap_servers=['localhost:9092'],
        group_id='db_sink_group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='earliest'
    )

    logger.info("📥 DB Sink Active: Committing results sequentially...")

    for message in consumer:
        result = message.value
        
        # SANITIZATION: Remove any fields not in the LanceDB schema
        # This prevents the 'Field not found' error
        clean_record = {k: v for k, v in result.items() if k in valid_fields}
        
        try:
            # Singleton write: No lock contention possible!
            table.add([clean_record]) 
            logger.info(f"💾 Indexed & Persisted: {clean_record.get('filename')}")
        except Exception as e:
            logger.error(f"❌ Failed to write record: {e}")

if __name__ == "__main__":
    run_db_sink()