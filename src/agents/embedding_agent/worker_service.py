import os
import json
import queue
from confluent_kafka import Consumer, Producer
from src.agents.embedding_agent.worker import _process_logic_with_updates

# Configuration
KAFKA_SERVER = os.getenv('KAFKA_BROKER_DOCKER', 'kafka:29092')
SOURCE_TOPICS = ['standard_tasks', 'paginated_tasks', 'jumbo_tasks']
RESULT_TOPIC = 'processed_content'

# Consumer for incoming tasks
c = Consumer({
    'bootstrap.servers': KAFKA_SERVER,
    'group.id': 'ocr-workers',
    'auto.offset.reset': 'earliest'
})

# Producer for forwarding extracted text to the Embedding Service
p = Producer({'bootstrap.servers': KAFKA_SERVER})

# Thread-safe dummy queue to satisfy the worker function signature
dummy_queue = queue.Queue()

def delivery_report(err, msg):
    if err is not None:
        print(f'❌ Worker failed to deliver result: {err}')

c.subscribe(SOURCE_TOPICS)

print(f"👷 Worker started. Listening to {SOURCE_TOPICS}...")

try:
    while True:
        msg = c.poll(1.0)
        if msg is None: continue
        if msg.error():
            print(f"Consumer error: {msg.error()}")
            continue

        task = json.loads(msg.value().decode('utf-8'))
        filename = task.get('filename', 'Unknown')
        worker_id = f"worker-{os.getpid()}" # Unique ID for dashboard rows
        
        print(f"📦 Processing: {filename}")
        
        # 1. SIGNAL START: Tell Dashboard to create a progress bar row
        start_signal = {
            "type": "START",
            "worker_id": worker_id,
            "filename": filename,
            "total": 1 # Initial placeholder; will be updated by chunks count
        }
        p.produce(RESULT_TOPIC, json.dumps(start_signal).encode('utf-8'))
        
        # 2. DO WORK: Passing dummy_queue prevents the NoneType 'put' error
        chunks = _process_logic_with_updates(task, dummy_queue, worker_id, task.get('page_range'))
        
        if chunks:
            # Update total chunks for dashboard bar accuracy
            p.produce(RESULT_TOPIC, json.dumps({
                "type": "START", 
                "worker_id": worker_id, 
                "filename": filename, 
                "total": len(chunks)
            }).encode('utf-8'))

            for chunk in chunks:
                # SCHEMA SAFETY: Remove non-db fields
                chunk.pop('page_range', None)
                chunk.pop('timestamp', None)
                
                # 3. SIGNAL DONE: This increments the global and worker bars
                chunk['type'] = "DONE"
                chunk['worker_id'] = worker_id
                
                p.produce(
                    RESULT_TOPIC, 
                    json.dumps(chunk).encode('utf-8'), 
                    callback=delivery_report
                )
            
            p.flush() # Ensure all signals are sent
            print(f"✅ Finished: {filename} ({len(chunks)} chunks sent)")

except KeyboardInterrupt:
    pass
finally:
    c.close()