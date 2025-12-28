import time

import os
# SILENCE WARNINGS: Must be set before importing transformers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import gc
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from sentence_transformers import SentenceTransformer
from src.common.db import get_table
from src.config.loader import SETTINGS

# 1. LOAD CONFIG
MODEL_NAME = SETTINGS['system']['model_name']
EXPECTED_DIM = SETTINGS['system']['model_dimension']

# MEMORY FIX:
# We match Batch Size to Max Workers (4).
# This ensures we process exactly one set of files, then STOP and FLUSH.
BATCH_SIZE = SETTINGS['system']['max_workers'] 

def process_file_wrapper(row_dict):
    """
    Worker Function: Extracts content from file.
    """
    # Lazy Import inside the process to keep it isolated
    from src.common.factory import ExtractorFactory
    from src.config.loader import SETTINGS

    filename = row_dict['filename']
    doc_id = row_dict['id']
    file_path = row_dict['file_path']
    
    raw_type = str(row_dict['file_type']).lower()
    file_type = raw_type if raw_type.startswith('.') else f".{raw_type}"
    
    extractor = ExtractorFactory.get_extractor(file_type)
    if not extractor:
        return []

    chunks = []
    try:
        # Extract content
        for page_num, content in extractor.extract(file_path):
            if not content: continue

            chunk_size = SETTINGS['system']['chunk_size']
            overlap = SETTINGS['system']['chunk_overlap']
            
            start = 0
            while start < len(content):
                end = start + chunk_size
                text_slice = content[start:end]
                
                embedding_input = f"Filename: {filename} Page: {page_num} Content: {text_slice}"
                
                record = row_dict.copy()
                record['id'] = f"{doc_id}_p{page_num}_{start}" 
                record['page_number'] = page_num
                record['content'] = text_slice
                record['_embedding_input'] = embedding_input 
                
                chunks.append(record)
                
                start += (chunk_size - overlap)
                if start >= len(content): break
            
    except Exception as e:
        print(f"❌ [Worker] Error processing {filename}: {e}")
    
    return chunks

def embed_documents():
    print(f"🧠 Active Brain: {MODEL_NAME} (Target: {EXPECTED_DIM} dim)")
    
    # Force settings refresh
    num_workers = SETTINGS['system']['max_workers']
    print(f"🚦 Parallel Mode: {num_workers} workers | Strict Batch Size: {BATCH_SIZE}")
    
    table = get_table()
    df = table.to_pandas()
    
    if df.empty:
        print("⚠️ Database is empty. Waiting for Scanner...")
        return

    # --- 1. DEDUPLICATION ---
    total_rows = len(df)
    df_clean = df.drop_duplicates(subset=['file_path'], keep='first')
    if len(df_clean) < total_rows:
        print(f"🧹 Removing {total_rows - len(df_clean)} duplicate rows...")
        table.delete("true")
        table.add(df_clean.to_dict('records'))
        df = df_clean

    # --- 2. IDENTIFY TASKS ---
    tasks = []
    files_to_delete = []
    has_vector_col = 'vector' in df.columns

    print(f"📊 Analyzing {len(df)} files for changes...")
    
    for _, row in df.iterrows():
        f_path = row['file_path']
        if not os.path.exists(f_path):
            files_to_delete.append(f_path)
            continue
            
        disk_mtime = os.path.getmtime(f_path)
        db_mtime = row.get('last_modified', 0)
        if pd.isna(db_mtime): db_mtime = 0
        
        val = row.get('vector')
        should_reindex = False
        
        if not has_vector_col: should_reindex = True
        elif val is None: should_reindex = True
        elif isinstance(val, float) and pd.isna(val): should_reindex = True
        elif hasattr(val, '__len__'):
            if len(val) != EXPECTED_DIM: should_reindex = True
            elif all(v == 0.0 for v in val): should_reindex = True
        
        if (disk_mtime - db_mtime > 1.0): should_reindex = True

        if should_reindex:
            files_to_delete.append(f_path) 
            tasks.append(row.to_dict())

    # --- 3. CLEANUP OLD DATA ---
    if files_to_delete:
        if len(files_to_delete) >= len(df):
             print("🧹 Full Re-Index detected. Wiping table...")
             table.delete("true")
        else:
            print(f"🧹 Cleaning {len(files_to_delete)} old entries...")
            batch_size = 50
            for i in range(0, len(files_to_delete), batch_size):
                batch = files_to_delete[i:i+batch_size]
                safe_names = [n.replace("'", "''") for n in batch]
                where_clause = f"file_path IN ({', '.join([repr(n) for n in safe_names])})"
                try: table.delete(where_clause)
                except: pass

    if not tasks:
        print("✅ Database is up to date.")
        return

    # --- 4. EXECUTION ---
    print(f"🚀 Processing {len(tasks)} files...")
    
    try:
        model = SentenceTransformer(MODEL_NAME, device='mps')
        print("   ✅ Neural Engine (MPS) Enabled for Embeddings")
    except:
        model = SentenceTransformer(MODEL_NAME)
        print("   ⚠️ Running on CPU")

    total_chunks_processed = 0
    start_time = time.time()

    # Iterate through tasks in chunks
    for i in range(0, len(tasks), BATCH_SIZE):
        batch_tasks = tasks[i : i + BATCH_SIZE]
        current_batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(tasks) // BATCH_SIZE) + 1
        
        print(f"   [Batch {current_batch_num}/{total_batches}] Processing {len(batch_tasks)} files...")
        
        batch_chunks = []
        
        # A. EXTRACT (CPU Parallel)
        # We RECREATE the executor for every batch or group of batches.
        # This is slightly slower but guarantees memory is freed.
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            results = executor.map(process_file_wrapper, batch_tasks)
            for res in results:
                batch_chunks.extend(res)
        
        if not batch_chunks:
            continue

        # B. EMBED & SAVE
        try:
            inputs = [c.pop('_embedding_input') for c in batch_chunks]
            
            # Embed
            vectors = model.encode(inputs, batch_size=32, show_progress_bar=False)
            
            current_time_val = time.time()
            for idx, rec in enumerate(batch_chunks):
                rec['vector'] = vectors[idx].tolist()
                rec['last_modified'] = current_time_val
            
            table.add(batch_chunks, mode="append")
            
            total_chunks_processed += len(batch_chunks)
            
        except Exception as e:
            print(f"     ❌ Batch Error: {e}")

        # C. FLUSH MEMORY
        del batch_chunks, inputs, vectors
        gc.collect()

    print(f"✅ Pipeline Complete. Processed {total_chunks_processed} chunks in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    embed_documents()