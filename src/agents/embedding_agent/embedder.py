import os
# SILENCE WARNINGS
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import time
import gc
import psutil
import torch
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from sentence_transformers import SentenceTransformer
from src.common.db import get_table
from src.common.storage import StorageProvider
from src.config.loader import SETTINGS

def init_worker():
    """
    Worker Setup: Loads the heavy models ONCE per process.
    """
    import logging
    logging.getLogger("ppocr").setLevel(logging.CRITICAL)
    logging.getLogger("paddlex").setLevel(logging.CRITICAL)
    
    try:
        from src.common.factory import ExtractorFactory
        from src.extractors.image import ocr_engine 
    except Exception as e:
        print(f"⚠️ Worker Init Failed: {e}")

def process_task_stateless(task):
    """
    Intelligent Worker:
    1. Extracts Text
    2. CLASSIFIES Document (Visa vs Tax, Dates, Country) <--- NEW
    3. Chunks & Attaches Metadata
    """
    from src.common.factory import ExtractorFactory
    # Import the Brain directly inside the worker to avoid pickle issues
    from src.agents.classification_agent.classifier import DocumentClassifier
    
    filename = task['filename']
    file_path = task['file_path']
    doc_id = task['id']
    
    chunks = []
    try:
        local_path = StorageProvider.get_file_path(file_path)
        
        raw_type = str(task['file_type']).lower()
        file_type = raw_type if raw_type.startswith('.') else f".{raw_type}"
        
        extractor = ExtractorFactory.get_extractor(file_type)
        if not extractor: return []
        
        # --- STEP 1: LOAD CONTENT ---
        # We consume the generator into a list so we can use the text twice:
        # Once for classification, Once for chunking.
        # (Personal docs are small enough for RAM)
        pages_content = list(extractor.extract(local_path))
        
        if not pages_content:
            return []

        # --- STEP 2: CLASSIFY & EXTRACT METADATA (The "Brain") ---
        # Combine first few pages to give the AI enough context (limit to 3000 chars)
        full_text_context = " ".join([p[1] for p in pages_content])[:3500]
        
        try:
            # Initialize the classifier (connects to Ollama/OpenAI)
            classifier = DocumentClassifier()
            # Ask the AI what this is
            metadata = classifier.classify(full_text_context)
        except Exception as ai_error:
            # Fallback if AI fails (don't stop the pipeline)
            # print(f"⚠️ AI Classification failed for {filename}: {ai_error}")
            metadata = {
                "category_id": "uncategorized",
                "issue_date": None,
                "expiry_date": None,
                "country": None,
                "person_name": None,
                "summary": "AI Classification Failed"
            }

        # --- STEP 3: CHUNK & ENRICH ---
        for page_num, content in pages_content:
            if not content: continue

            chunk_size = 1000 
            overlap = 100
            start = 0
            while start < len(content):
                end = start + chunk_size
                text_slice = content[start:end]
                
                # We inject the "category" into the embedding input 
                # This helps semantic search find "Visas" even if the word "Visa" isn't in the chunk
                category_hint = metadata.get('category_id', '').replace('_', ' ')
                embedding_input = f"Type: {category_hint} | Filename: {filename} | Content: {text_slice}"
                
                record = task.copy()
                record['id'] = f"{doc_id}_p{page_num}_{start}"
                record['page_number'] = page_num
                record['content'] = text_slice
                record['_embedding_input'] = embedding_input 
                
                # --- ATTACH SMART METADATA TO DB RECORD ---
                # These fields are now searchable in LanceDB!
                record['category'] = metadata.get('category_id')
                record['issue_date'] = metadata.get('issue_date')
                record['expiry_date'] = metadata.get('expiry_date')
                record['country'] = metadata.get('country')
                record['person'] = metadata.get('person_name')
                record['summary'] = metadata.get('summary')
                
                chunks.append(record)
                
                start += (chunk_size - overlap)
                if start >= len(content): break
                
    except Exception as e:
        pass
        
    return chunks

def get_best_device():
    if torch.cuda.is_available():
        print("   ✅ Hardware: Nvidia GPU (CUDA) Detected")
        return 'cuda'
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print("   ✅ Hardware: Apple Silicon (MPS) Detected")
        return 'mps'
    print("   ⚠️ Hardware: No GPU detected. Running on CPU.")
    return 'cpu'

def embed_documents():
    MODEL_NAME = SETTINGS['system']['model_name']
    MAX_WORKERS = psutil.cpu_count(logical=True) or 4
    EXPECTED_DIM = SETTINGS['system']['model_dimension']
    
    print(f"🧠 Active Brain: {MODEL_NAME}")
    print(f"🏭 Production Line: Up to {MAX_WORKERS} Parallel Workers")
    
    table = get_table()
    df = table.to_pandas()
    
    if df.empty:
        print("⚠️ Database is empty. Waiting for Scanner...")
        return

    tasks = []
    df_clean = df.drop_duplicates(subset=['file_path'], keep='first')
    files_to_delete = []
    has_vector_col = 'vector' in df.columns
    
    print(f"📊 Analyzing {len(df)} files via StorageProvider...")

    for _, row in df_clean.iterrows():
        f_path = row['file_path']
        if not StorageProvider.exists(f_path):
            files_to_delete.append(f_path)
            continue
            
        disk_mtime = StorageProvider.get_last_modified(f_path)
        db_mtime = row.get('last_modified', 0)
        if pd.isna(db_mtime): db_mtime = 0
        
        val = row.get('vector')
        should_reindex = False
        if not has_vector_col or val is None: should_reindex = True
        elif isinstance(val, float) and pd.isna(val): should_reindex = True
        elif hasattr(val, '__len__') and (len(val) != EXPECTED_DIM or all(v==0.0 for v in val)): should_reindex = True
        if (disk_mtime - db_mtime > 1.0): should_reindex = True

        if should_reindex:
            files_to_delete.append(f_path)
            tasks.append(row.to_dict())

    if files_to_delete:
        print(f"🧹 Pruning {len(files_to_delete)} stale records...")
        safe_names = [n.replace("'", "''") for n in files_to_delete]
        if safe_names:
            batch_size = 50
            for i in range(0, len(safe_names), batch_size):
                batch = safe_names[i:i+batch_size]
                try: table.delete(f"file_path IN ({', '.join([repr(n) for n in batch])})")
                except: pass

    if not tasks:
        print("✅ System Synced. No new tasks.")
        return

    print(f"🔥 Processing {len(tasks)} tasks...")
    
    target_device = get_best_device()
    try:
        embed_model = SentenceTransformer(MODEL_NAME, device=target_device)
    except Exception as e:
        print(f"   ⚠️ Model Init Error: {e}. Falling back to CPU.")
        embed_model = SentenceTransformer(MODEL_NAME, device='cpu')

    total_processed = 0
    start_time = time.time()
    
    active_futures = set()
    task_iterator = iter(tasks)
    
    RAM_TARGET = 80.0
    RAM_CRITICAL = 92.0
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS, initializer=init_worker) as executor:
        
        while True:
            mem = psutil.virtual_memory()
            can_submit = True
            
            if mem.percent > RAM_CRITICAL:
                can_submit = False
                if len(active_futures) > 0:
                    print(f"   🛑 Resource Pressure ({mem.percent}%). Throttling Ingestion...")
            elif mem.percent > RAM_TARGET:
                if len(active_futures) >= (MAX_WORKERS // 2):
                    can_submit = False

            while can_submit and len(active_futures) < MAX_WORKERS:
                try:
                    task = next(task_iterator)
                    future = executor.submit(process_task_stateless, task)
                    active_futures.add(future)
                except StopIteration:
                    can_submit = False
                    break
            
            if not active_futures and not can_submit: 
                break 
            
            done_futures = [f for f in active_futures if f.done()]
            
            for f in done_futures:
                active_futures.remove(f)
                try:
                    result_chunks = f.result()
                    if result_chunks:
                        inputs = [c.pop('_embedding_input') for c in result_chunks]
                        vectors = embed_model.encode(inputs, batch_size=32, show_progress_bar=False)
                        
                        curr_t = time.time()
                        for idx, rec in enumerate(result_chunks):
                            rec['vector'] = vectors[idx].tolist()
                            rec['last_modified'] = curr_t
                        
                        table.add(result_chunks, mode="append")
                        total_processed += len(result_chunks)
                        print(f"   ✅ Indexed {len(result_chunks)} chunks. RAM: {mem.percent}%")
                except Exception as e:
                    print(f"   ❌ Task Failed: {e}")

            if not done_futures:
                time.sleep(0.05)

    print(f"✅ Pipeline Complete. Processed {total_processed} chunks in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    embed_documents()