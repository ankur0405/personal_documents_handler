import json
from kafka import KafkaConsumer, KafkaProducer
from src.config.loader import config

def retry_dlq():
    print("🔄 Initializing DLQ Recovery...")
    
    # Consumer for the DLQ
    consumer = KafkaConsumer(
        'document_tasks_failed',
        bootstrap_servers=config.kafka_broker,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='dlq_recovery_group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    # Producer for the Main Queue
    producer = KafkaProducer(
        bootstrap_servers=config.kafka_broker,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    count = 0
    # Poll for messages (non-blocking for CLI usage)
    messages = consumer.poll(timeout_ms=5000)
    
    for tp, msg_list in messages.items():
        for msg in msg_list:
            original_task = msg.value.get("original_task")
            if original_task:
                # Increment retry count for monitoring
                original_task["retry_count"] = original_task.get("retry_count", 0) + 1
                
                producer.send('document_tasks', original_task)
                count += 1

    producer.flush()
    print(f"✅ Successfully re-queued {count} tasks for processing.")

if __name__ == "__main__":
    retry_dlq()