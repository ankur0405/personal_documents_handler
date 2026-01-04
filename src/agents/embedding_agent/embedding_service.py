import os
import json
import torch
import numpy as np
from confluent_kafka import Consumer
from sentence_transformers import SentenceTransformer
from src.common.db import get_table
from dotenv import load_dotenv

load_dotenv()

# 1. Configuration - Optimized for your 64GB Mac
BATCH_SIZE = 32 
device = 'mps' if torch.backends.mps.is_available() else 'cpu'

# 2. Initialize DB and Model
table = get_table()
model_name = os.getenv('MODEL_NAME', 'all-MiniLM-L6-v2')
model = SentenceTransformer(model_name, device=device)

# 3. Kafka Configuration
c = Consumer({
    'bootstrap.servers': os.getenv('KAFKA_BROKER', 'localhost:9092'),
    'group.id': 'embedding-group-v2',  # <--- Change this name
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True
})
c.subscribe(['processed_content'])

print(f"✅ Auto-Tune: High Performance | Workers: 8 | Device: {device}")
print(f"✅ Hardware: 64GB Mac | Batch Size: {BATCH_SIZE} | Device: {device}")
print(f"🚀 Embedding Service started on {device}...")

batch_buffer = []

try:
    while True:
        msg = c.poll(1.0)
        
        if msg is not None and not msg.error():
            try:
                data = json.loads(msg.value().decode('utf-8'))
                
                # FILTER: Only process completed document chunks
                if data.get('type') == 'DONE' and '_embedding_input' in data:
                    batch_buffer.append(data)
                else:
                    continue
            except Exception as e:
                print(f"Error parsing message: {e}")
                continue

        # 4. Batch Processing and Vectorization
        if len(batch_buffer) >= BATCH_SIZE or (msg is None and len(batch_buffer) > 0):
            try:
                # Prepare inputs for the model
                inputs = [item.pop('_embedding_input') for item in batch_buffer]
                
                # Generate vectors using Apple Silicon GPU (MPS)
                vectors = model.encode(inputs, batch_size=len(inputs), show_progress_bar=False)

                for idx, item in enumerate(batch_buffer):
                    # SCHEMA CLEANUP: Remove all metadata not defined in LanceDB
                    item.pop('type', None)
                    item.pop('topic', None)     # Prevents "Field topic not found"
                    item.pop('step', None)      # Prevents "Field step not found"
                    item.pop('worker_id', None) # Prevents "Field worker_id not found"
                    
                    # Map the generated vector to the database row
                    item['vector'] = vectors[idx].tolist()
                
                # Commit cleaned batch to LanceDB
                table.add(batch_buffer, mode="append")
                print(f"✅ Committed {len(batch_buffer)} chunks to LanceDB.")
                batch_buffer = []
                
            except Exception as e:
                print(f"❌ Batch processing failed: {e}")
                # Clear buffer on failure to prevent infinite loops of the same error
                batch_buffer = []

except KeyboardInterrupt:
    print("Stopping Embedding Service...")
finally:
    c.close()