import os
import re
import time
import gc
import logging
import queue
import traceback
from src.common.factory import ExtractorFactory
from src.agents.classification_agent.classifier import DocumentClassifier
from src.common.storage import StorageProvider
from src.config.loader import SETTINGS

def count_pages_fast(filepath):
    """
    Counts /Page entries in PDF binary for fast approximation.
    Used by the Producer to decide on slicing.
    """
    try:
        with open(filepath, "rb") as f:
            return len(re.findall(br"/Type\s*/Page\b", f.read()))
    except:
        return 1

def worker_entrypoint(task_queue, result_queue, worker_id):
    """
    Standard worker process that picks tasks, extracts text, 
    and communicates progress to the Supervisor.
    """
    logging.getLogger("ppocr").setLevel(logging.CRITICAL)
    logging.getLogger("paddlex").setLevel(logging.CRITICAL)

    pid = os.getpid()

    while True:
        try:
            try:
                task = task_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if task is None: break 

            filename = task['filename']
            local_path = StorageProvider.get_file_path(task['file_path'])
            p_range = task.get('page_range') # Tuple e.g. (1, 5)
            
            # 1. SIGNAL START
            # Calculate total pages for this specific slice for the progress bar
            total_in_slice = p_range[1] - p_range[0] + 1 if p_range else 1
            
            result_queue.put({
                "type": "START",
                "worker_id": worker_id,
                "filename": filename if not p_range else f"{filename}[p{p_range[0]}-{p_range[1]}]",
                "total": total_in_slice,
                "task": task
            })
            
            # 2. DO WORK
            start_t = time.time()
            chunks = _process_logic_with_updates(task, result_queue, worker_id, p_range)
            duration = time.time() - start_t
            
            # 3. SIGNAL DONE
            result_queue.put({
                "type": "DONE",
                "worker_id": worker_id,
                "pid": pid,
                "success": True,
                "data": chunks,
                "duration": duration,
                "task": task
            })
            
            # Aggressive cleanup to prevent RAM bloat
            del chunks
            gc.collect()
            
        except queue.Empty: 
            continue
        except Exception as e:
            result_queue.put({
                "type": "DONE",
                "worker_id": worker_id,
                "pid": pid,
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "task": task
            })

def _process_logic_with_updates(task, result_queue, worker_id, p_range):
    """Internal logic to extract text, classify document, and create chunks."""
    filename = task['filename']
    local_path = StorageProvider.get_file_path(task['file_path'])
    
    # Determine extension and get extractor
    _, ext = os.path.splitext(filename)
    f_type = task.get('file_type', ext.lower())
    if not f_type.startswith('.'): 
        f_type = f".{f_type}"

    extractor = ExtractorFactory.get_extractor(f_type)
    if not extractor: 
        return []
    
    # Slicing logic: We iterate through the generator and filter by range
    pages_generator = extractor.extract(local_path)
    page_buffer = []
    
    start_p, end_p = p_range if p_range else (1, 999999)
    
    for i, (p_num, content) in enumerate(pages_generator, 1):
        # Skip pages outside the slice
        if i < start_p: 
            continue
        if i > end_p: 
            break
        
        page_buffer.append((p_num, content))
        
        # UI UPDATE: Send progress for every page in the slice
        result_queue.put({
            "type": "PROGRESS",
            "worker_id": worker_id,
            "current": i - start_p + 1
        })

    # Join the text for classification (limited to 3500 chars for speed)
    full_text = " ".join([p[1] for p in page_buffer])[:3500]
    try:
        meta = DocumentClassifier().classify(full_text, filename=filename)
    except:
        meta = {"category_id": "uncategorized"}

    c_size = SETTINGS['system'].get('chunk_size', 1000)
    c_over = SETTINGS['system'].get('chunk_overlap', 100)
    chunks = []

    for p_num, content in page_buffer:
        if not content: 
            continue
            
        start = 0
        while start < len(content):
            end = start + c_size
            slice_text = content[start:end]
            
            # Map extracted metadata to the schema-compliant record
            rec = task.copy()
            rec.update({
                'id': f"{task['id']}_p{p_num}_{start}", # Unique ID for parallel slices
                'page_number': p_num,
                'content': slice_text,
                '_embedding_input': f"Type: {meta.get('category_id')} | Content: {slice_text[:500]}",
                'category': meta.get('category_id'),
                'issue_date': meta.get('issue_date'),
                'expiry_date': meta.get('expiry_date', ''),
                'country': meta.get('country', ''),
                'person': meta.get('person_name', ''),
                'summary': meta.get('summary', '')
            })
            chunks.append(rec)
            
            start += (c_size - c_over)
            if start >= len(content):
                break
            
    return chunks