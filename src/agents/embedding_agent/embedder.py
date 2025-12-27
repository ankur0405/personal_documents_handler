"""
Module: Embedding Agent
Description: Loads a local Transformer model to generate vector embeddings for documents.
             Optimized for Apple Silicon (MPS) acceleration.

Technical Details:
- Model: 'all-MiniLM-L6-v2' (384-dimensional dense vectors).
- Hardware: Automatically detects 'mps' (Metal) on macOS, falls back to 'cpu'.
- Strategy: Fetches metadata from LanceDB, generates embeddings in batches,
            and performs a 'Merge/Insert' update to save vectors.
"""

import torch
import time
from sentence_transformers import SentenceTransformer
from src.common.db import get_table

# --- CONFIGURATION ---
# The model name from HuggingFace.
# 'all-MiniLM-L6-v2' is the industry standard for efficiency/accuracy balance.
MODEL_NAME = 'all-MiniLM-L6-v2'
BATCH_SIZE = 64  # Process 64 docs at a time on GPU

def get_device():
    """
    Detects the best available hardware accelerator.
    Returns 'mps' for Mac, 'cuda' for Nvidia, or 'cpu'.
    """
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu"

def embed_documents():
    """
    Main routine:
    1. Loads the Model.
    2. Fetches documents from DB.
    3. Generates Vectors.
    4. Updates DB.
    """

    # 1. Setup Hardware
    device = get_device()
    print(f"🚀 AI Hardware Accelerator: {device.upper()}")

    print(f"📥 Loading Model: {MODEL_NAME}...")
    # Initialize the model and move it to the GPU memory
    model = SentenceTransformer(MODEL_NAME, device=device)

    # 2. Fetch Data
    table = get_table()
    # Convert LanceDB table to Pandas for easy iteration.
    # Note: For <100k docs, loading into RAM is fine. For millions, we'd use an iterator.
    df = table.to_pandas()

    if df.empty:
        print("⚠️  No documents found in database to embed.")
        return

    print(f"🧠 Processing {len(df)} documents...")
    start_time = time.time()

    # 3. Prepare Text for Embedding
    # Current Strategy: Embed "Filename + Path".
    # This enables semantic search like "Find tax documents" matching "2024_IRS_Form.pdf"
    # (Future Phase: We will add full file content here).
    texts_to_embed = [
        f"Filename: {row['filename']}  Context: {row['file_path']}"
        for _, row in df.iterrows()
    ]

    # 4. Generate Embeddings (The Heavy Lifting)
    # show_progress_bar=True gives us a nice visual in the terminal
    embeddings = model.encode(texts_to_embed, batch_size=BATCH_SIZE, show_progress_bar=True)

    end_time = time.time()
    duration = end_time - start_time
    print(f"✅ Embedded {len(df)} docs in {duration:.2f} seconds ({len(df)/duration:.1f} docs/sec)")

    # 5. Prepare Updates
    # We need to construct a list of dictionaries to merge back into LanceDB.
    # We map the computed vector back to the document ID.
    updated_data = []
    for index, row in df.iterrows():
        record = row.to_dict()
        record['vector'] = embeddings[index] # Inject the new 384-dim vector
        updated_data.append(record)

    # 6. Save to Database (Upsert)
    # merge_insert ensures we update existing rows based on the Primary Key ('id')
    # instead of creating duplicates.
    table.merge_insert(updated_data)
    print("💾 Database successfully updated with AI Vectors.")

if __name__ == "__main__":
    embed_documents()