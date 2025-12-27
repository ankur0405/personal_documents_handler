import time
import os
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from sentence_transformers import SentenceTransformer
from src.common.db import get_table
from src.common.factory import ExtractorFactory
from src.config.loader import SETTINGS

MODEL_NAME = 'all-MiniLM-L6-v2'

def process_file_wrapper(row_dict):
    """
    Worker Function: Extracts content from file.
    """
    filename = row_dict['filename']
    doc_id = row_dict['id']
    file_path = row_dict['file_path']
    
    # Normalize Extension
    raw_type = str(row_dict['file_type']).lower()
    file_type = raw_type if raw_type.startswith('.') else f".{raw_type}"
    
    extractor = ExtractorFactory.get_extractor(file_type)
    if not extractor:
        return []

    chunks = []
    try:
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
    table = get_table()
    df = table.to_pandas()
    
    if df.empty:
        print("⚠️ Database is empty. Waiting for Scanner...")
        return

    # --- 1. DEDUPLICATION (Self-Healing) ---
    # If the Scanner inserted the same file path multiple times, keep only one.
    total_rows = len(df)
    df_clean = df.drop_duplicates(subset=['file_path'], keep='first')
    
    if len(df_clean) < total_rows:
        diff = total_rows - len(df_clean)
        print(f"🧹 Detecting {diff} duplicate 'Skeleton' rows. Cleaning DB...")
        # We wipe the DB and re-insert the clean list (Metadata only) 
        # This is safer than trying to delete specific rows by ID which might be shared.
        table.delete("true") # Delete All
        table.add(df_clean.to_dict('records')) # Re-add clean rows
        df = df_clean # Update memory reference
        print("✅ DB Sanitized.")

    print(f"📊 Analyzing {len(df)} files...")

    # --- 2. CHANGE DETECTION ---
    tasks = []
    files_to_delete = []
    
    # Check if 'vector' column even exists (Fresh DB scenario)
    has_vector_col = 'vector' in df.columns

    for _, row in df.iterrows():
        f_path = row['file_path']
        f_name = row['filename']
        
        if not os.path.exists(f_path):
            print(f"🗑️  File deleted: {f_name}")
            files_to_delete.append(f_path)
            continue
            
        # Logic: Update if (No Vector) OR (File Changed on Disk)
        disk_mtime = os.path.getmtime(f_path)
        db_mtime = row.get('last_modified', 0)
        if pd.isna(db_mtime): db_mtime = 0
        
        # Is the vector missing/empty?
        is_empty = False
        if not has_vector_col:
            is_empty = True
        else:
            # Check if value is None or NaN
            val = row.get('vector')
            if val is None: is_empty = True
            elif isinstance(val, float) and pd.isna(val): is_empty = True # Handle NaN
        
        # If file is newer (>1s diff) OR it has no brains yet
        if is_empty or (disk_mtime - db_mtime > 1.0):
            reason = "New/Empty" if is_empty else "Modified"
            # print(f"🔄 Refreshing ({reason}): {f_name}")
            files_to_delete.append(f_path) 
            tasks.append(row.to_dict())

    # --- 3. CLEANUP & EXECUTION ---
    if files_to_delete:
        print(f"🧹 Clearing old data for {len(files_to_delete)} files...")
        for f_path in files_to_delete:
            safe_path = f_path.replace("'", "''")
            table.delete(f"file_path = '{safe_path}'")

    if not tasks:
        print("✅ No changes detected. Database is up to date.")
        return

    print(f"🚀 Processing {len(tasks)} files with {SETTINGS['system']['max_workers']} workers...")
    
    all_chunks = []
    start_read = time.time()
    
    with ProcessPoolExecutor(max_workers=SETTINGS['system']['max_workers']) as executor:
        results = executor.map(process_file_wrapper, tasks)
        for res in results:
            all_chunks.extend(res)
            
    print(f"✅ Generated {len(all_chunks)} chunks in {time.time() - start_read:.2f}s")

    if not all_chunks:
        print("⚠️ No content extracted from files.")
        return

    print(f"🧠 Embedding {len(all_chunks)} chunks...")
    model = SentenceTransformer(MODEL_NAME)
    
    inputs = [c.pop('_embedding_input') for c in all_chunks]
    vectors = model.encode(inputs, batch_size=64, show_progress_bar=True)
    
    current_time = time.time()
    for i, rec in enumerate(all_chunks):
        rec['vector'] = vectors[i].tolist()
        rec['last_modified'] = current_time
        
    print("💾 Saving to LanceDB...")
    table.add(all_chunks, mode="append")
    print("✅ Sync Complete.")

if __name__ == "__main__":
    embed_documents()