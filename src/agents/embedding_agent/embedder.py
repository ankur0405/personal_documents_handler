"""
Module: Embedding Agent (Robust)
Description: Generates AI embeddings and uses 'Overwrite' mode to ensure
             vectors are persisted to disk.
"""

import torch
import time
import numpy as np
from sentence_transformers import SentenceTransformer
from src.common.db import get_table

MODEL_NAME = 'all-MiniLM-L6-v2'
BATCH_SIZE = 64

def get_device():
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu"

def embed_documents():
    # 1. Setup Hardware
    device = get_device()
    print(f"🚀 AI Hardware Accelerator: {device.upper()}")
    
    print(f"📥 Loading Model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME, device=device)
    
    # 2. Fetch Data
    table = get_table()
    df = table.to_pandas()
    
    if df.empty:
        print("⚠️  No documents found in database.")
        return

    print(f"🧠 Processing {len(df)} documents...")
    start_time = time.time()

    # 3. Prepare Text
    texts_to_embed = [
        f"Filename: {row['filename']}  Context: {row['file_path']}" 
        for _, row in df.iterrows()
    ]

    # 4. Generate Embeddings
    embeddings = model.encode(texts_to_embed, batch_size=BATCH_SIZE, show_progress_bar=True)
    
    end_time = time.time()
    print(f"✅ Embedded {len(df)} docs in {end_time - start_time:.2f} seconds.")

    # 5. Prepare Payload
    updated_data = []
    
    # DEBUG: Print the first vector to prove it exists in memory
    print(f"🔍 DEBUG: First Vector Sample (Memory): {embeddings[0][:5]}")

    for index, row in df.iterrows():
        record = row.to_dict()
        
        # Convert Numpy -> List (Strict Serialization)
        vector_list = embeddings[index].tolist()
        record['vector'] = vector_list 
        updated_data.append(record)

    # 6. Save to Database (The Nuclear Fix)
    # We use mode="overwrite". Since 'updated_data' contains the FULL dataset 
    # (old metadata + new vectors), replacing the table is safe and atomic.
    print("💾 Overwriting database table...")
    table.add(updated_data, mode="overwrite")
    print("✅ Database successfully updated.")

if __name__ == "__main__":
    embed_documents()