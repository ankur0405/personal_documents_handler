import os
import re
import time
import gc
import logging
import queue
from src.common.factory import ExtractorFactory
from src.agents.classification_agent.classifier import DocumentClassifier
from src.common.storage import StorageProvider
from src.config.loader import SETTINGS

def count_pages_fast(filepath):
    try:
        with open(filepath, "rb") as f:
            # Counts /Page entries in PDF binary (fast approximation)
            return len(re.findall(br"/Type\s*/Page\b", f.read()))
    except:
        return 1

def worker_entrypoint(task_queue, result_queue, worker_id):
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
            
            # Estimate pages
            total_pages = 1
            if filename.lower().endswith('.pdf'):
                total_pages = count_pages_fast(local_path)
                if total_pages == 0: total_pages = 1

            # 1. SIGNAL START
            result_queue.put({
                "type": "START",
                "worker_id": worker_id,
                "pid": pid,
                "filename": filename,
                "total": total_pages
            })
            
            # 2. DO WORK
            start_t = time.time()
            chunks = _process_logic_with_updates(task, result_queue, worker_id, pid, total_pages)
            duration = time.time() - start_t
            
            # 3. SIGNAL DONE
            result_queue.put({
                "type": "DONE",
                "worker_id": worker_id,
                "pid": pid,
                "success": True,
                "data": chunks,
                "duration": duration
            })
            
            del chunks
            gc.collect()
            
        except Exception as e:
            result_queue.put({
                "type": "DONE",
                "worker_id": worker_id,
                "pid": pid,
                "success": False,
                "error": str(e),
                "task": task 
            })

def _process_logic_with_updates(task, result_queue, worker_id, pid, total_pages):
    filename = task['filename']
    local_path = StorageProvider.get_file_path(task['file_path'])
    
    if 'file_type' in task:
            raw = str(task['file_type']).lower()
            f_type = raw if raw.startswith('.') else f".{raw}"
    else:
            _, ext = os.path.splitext(filename)
            f_type = ext.lower()

    extractor = ExtractorFactory.get_extractor(f_type)
    if not extractor: return []
    
    pages_generator = extractor.extract(local_path)
    page_buffer = []
    
    last_update_time = time.time()
    
    for i, (p_num, content) in enumerate(pages_generator):
        page_buffer.append((p_num, content))
        
        # THROTTLE: Update UI max every 0.3s
        if time.time() - last_update_time > 0.3:
            result_queue.put({
                "type": "PROGRESS",
                "worker_id": worker_id,
                "current": i + 1
            })
            last_update_time = time.time()

    # Final "100%" update
    result_queue.put({"type": "PROGRESS", "worker_id": worker_id, "current": total_pages})

    full_text = " ".join([p[1] for p in page_buffer])[:3500]
    try:
        meta = DocumentClassifier().classify(full_text, filename=filename)
    except:
        meta = {"category_id": "uncategorized"}

    c_size = SETTINGS['system'].get('chunk_size', 1000)
    c_over = SETTINGS['system'].get('chunk_overlap', 100)
    chunks = []

    for p_num, content in page_buffer:
        if not content: continue
        start = 0
        while start < len(content):
            end = start + c_size
            slice_text = content[start:end]
            hint = str(meta.get('category_id', '')).replace('_', ' ')
            emb_input = f"Type: {hint} | Filename: {filename} | Content: {slice_text}"
            
            rec = task.copy()
            rec.update({
                'id': f"{task['id']}_p{p_num}_{start}",
                'page_number': p_num,
                'content': slice_text,
                '_embedding_input': emb_input,
                'category': meta.get('category_id'),
                'issue_date': meta.get('issue_date'),
                'expiry_date': meta.get('expiry_date'),
                'country': meta.get('country'),
                'person': meta.get('person_name'),
                'summary': meta.get('summary')
            })
            chunks.append(rec)
            start += (c_size - c_over)
            if start >= len(content): break
            
    return chunks