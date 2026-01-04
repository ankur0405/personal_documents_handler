import os
import json
import pathlib
import time
from confluent_kafka import Producer

# Configuration
KAFKA_SERVER = os.getenv('KAFKA_BROKER_DOCKER', 'kafka:29092')
SCAN_PATH = os.getenv('SCAN_PATH', '/data/raw')

# Initialize Kafka Producer
p = Producer({'bootstrap.servers': KAFKA_SERVER})

def delivery_report(err, msg):
    if err is not None:
        print(f'❌ Message delivery failed: {err}')

def simple_triage(filepath):
    """Simple triage logic to route files to the correct Kafka topic."""
    ext = pathlib.Path(filepath).suffix.lower()
    
    # Logic: Large files or specific types can go to different queues
    topic = 'standard_tasks'
    if ext == '.pdf':
        # Optional: Add logic here to check file size for 'jumbo_tasks'
        topic = 'paginated_tasks'
    
    return {
        'filename': os.path.basename(filepath),
        'file_path': filepath,
        'topic': topic,
        'step': 'OCR_START'
    }

def run_producer():
    print(f"📂 Starting recursive scan on: {SCAN_PATH}")
    root = pathlib.Path(SCAN_PATH)
    
    files = []
    # Manually iterate to catch permission errors on individual files
    for f in root.rglob('*'):
        try:
            # Skip hidden macOS resource forks immediately
            if f.name.startswith('._'):
                continue
            if f.is_file():
                files.append(f)
        except (PermissionError, OSError):
            # Log and skip files the container isn't allowed to touch
            print(f"⚠️ Skipping inaccessible file: {f.name}")
            continue
    
    print(f"🔍 Found {len(files)} total files. Beginning Ingestion...")

    for file_path in files:
        task = simple_triage(str(file_path))
        topic = task.get('topic', 'standard_tasks')
        
        p.produce(
            topic, 
            json.dumps(task).encode('utf-8'), 
            callback=delivery_report
        )
        # Flush frequently to prevent memory pressure
        if len(files) > 100:
            p.poll(0) 

    print("⏳ Flushing producer queue...")
    p.flush()
    print(f"🏁 Ingestion scan complete. {len(files)} tasks sent to Kafka.")
    
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    run_producer()