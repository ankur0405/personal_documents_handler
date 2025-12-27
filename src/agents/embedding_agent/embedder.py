"""
Module: Embedding Agent (Page-Level Chunking)
Description: Breaks documents into pages, embeds each page separately, 
             and saves them as distinct searchable records.
"""

import torch
import time
from sentence_transformers import SentenceTransformer
from src.common.db import get_table
# Import the new 'extract_pages' generator
from src.common.content_extractor import extract_pages

MODEL_NAME = 'all-MiniLM-L6-v2'
BATCH_SIZE = 64
MAX_TEXT_PER_PAGE = 1000 # Truncate PER PAGE, not per file.

def get_device():
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu"

def embed_documents():
    device = get_device()
    print(f"🚀 AI Hardware Accelerator: {device.upper()}")
    
    print(f"📥 Loading Model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME, device=device)
    
    # 1. Fetch Metadata (The File List)
    table = get_table()
    df = table.to_pandas()
    
    # We only want unique files. If the DB already has page chunks, we might get duplicates
    # if we blindly re-run. 
    # STRATEGY: We assume 'df' contains the Metadata Scans (page_number=1 default).
    # Since we are doing a "Nuclear Reset" anyway, this simple logic holds.
    
    if df.empty:
        print("⚠️  No documents found.")
        return

    print(f"🧠 Chunking and Embedding {len(df)} files...")
    start_time = time.time()

    texts_to_embed = []
    chunked_records = []
    
    for index, row in df.iterrows():
        # Generator: Returns (1, "text..."), (2, "text...")
        for page_num, raw_text in extract_pages(row['file_path'], row['file_type']):
            
            # Clean text
            clean_text = raw_text[:MAX_TEXT_PER_PAGE].replace("\n", " ")
            
            # Semantic Payload: Include Page Number in the context!
            # This helps the AI understand "Page 30 of Passport"
            embedding_input = f"Filename: {row['filename']} Page: {page_num} Content: {clean_text}"
            texts_to_embed.append(embedding_input)
            
            # Create a New Record for this Page
            new_record = row.to_dict()
            new_record['id'] = f"{row['id']}_p{page_num}" # Unique ID per page
            new_record['page_number'] = page_num
            new_record['content'] = clean_text
            
            chunked_records.append(new_record)

    # 2. Generate Vectors
    print(f"⚡ Generating vectors for {len(chunked_records)} pages...")
    if not chunked_records:
        print("❌ No text content extracted from any file.")
        return

    embeddings = model.encode(texts_to_embed, batch_size=BATCH_SIZE, show_progress_bar=True)
    
    end_time = time.time()
    print(f"✅ Embedded {len(chunked_records)} pages in {end_time - start_time:.2f} seconds.")

    # 3. Merge and Save
    final_payload = []
    for i, record in enumerate(chunked_records):
        record['vector'] = embeddings[i].tolist()
        final_payload.append(record)

    print("💾 Saving Page-Level Index to database...")
    table.add(final_payload, mode="overwrite")
    print("✅ Database successfully updated.")

if __name__ == "__main__":
    embed_documents()