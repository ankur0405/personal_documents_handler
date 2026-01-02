import os
import time
import psutil
import torch
import multiprocessing
import queue
import json
from sentence_transformers import SentenceTransformer

# Local Imports
from src.common.db import get_table
from src.config.loader import SETTINGS
from src.agents.embedding_agent.dashboard import Dashboard
from src.agents.embedding_agent.worker import worker_entrypoint, count_pages_fast

def get_best_device():
    if torch.cuda.is_available(): return 'cuda'
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available(): return 'mps'
    return 'cpu'

def determine_action(error_msg):
    """Heuristic to suggest fixes for failures"""
    msg = str(error_msg).lower()
    if "timeout" in msg: return "File too complex: Split into smaller PDFs"
    if "memory" in msg or "kill" in msg: return "Out of RAM: Reduce Chunk Size or Split File"
    if "password" in msg or "encrypted" in msg: return "Remove Password Protection"
    if "empty" in msg or "no text" in msg: return "Scanned PDF? OCR might have failed"
    if "corrupt" in msg: return "File Corrupted: Check Integrity"
    return "Check Logs / Retry Manually"

def run_batch_processing(tasks, model, table, min_workers=5, max_workers=12, ram_limit_mb=4000, time_limit_sec=300, phase_name="Main"):
    if not tasks: return []

    dashboard = Dashboard(len(tasks), min_workers, title=f"Pipeline: {phase_name}")
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    workers = {}
    worker_map = {}

    # State tracking: { worker_index: {'start_time': float, 'filename': str} }
    worker_state = {}

    detailed_failures = [] # List of dicts {filename, path, error, action}

    # Load performance constraints from settings
    ram_limit_pct = SETTINGS['performance'].get('ram_limit_percent', 80.0)

    def spawn(idx):
        p = multiprocessing.Process(target=worker_entrypoint, args=(task_queue, result_queue, idx))
        p.start()
        workers[p.pid] = p
        worker_map[p.pid] = idx
        worker_state[idx] = None
        return p

    print(f"\n🚀 {phase_name}: {len(tasks)} files | Auto-Scale: {min_workers}-{max_workers} Workers")
    for i in range(min_workers): spawn(i)
    current_worker_index = min_workers

    for t in tasks: task_queue.put(t)

    completed = 0
    total = len(tasks)
    last_scale_check = time.time()

    while completed < total:
        # A. Process Results
        for _ in range(50):
            try:
                msg = result_queue.get_nowait()
                w_idx = msg.get('worker_id', -1)

                if msg['type'] == 'START':
                    dashboard.set_worker_task(w_idx, msg['filename'], msg['total'])
                    # Capture task data so we can retry on Timeout
                    worker_state[w_idx] = {
                        'start_time': time.time(), 
                        'filename': msg['filename'],
                        'task': msg.get('task') 
                    }

                elif msg['type'] == 'PROGRESS':
                    dashboard.update_worker_progress(w_idx, msg['current'])
                    # Heartbeat: Reset timeout clock if it's making progress
                    if worker_state.get(w_idx): worker_state[w_idx]['start_time'] = time.time()

                elif msg['type'] == 'DONE':
                    completed += 1
                    dashboard.set_worker_task(w_idx, "Idle", 1)
                    dashboard.update_worker_progress(w_idx, 0)
                    worker_state[w_idx] = None

                    if msg['success']:
                        chunk_data = msg['data']
                        if chunk_data:
                            # 1. Prepare inputs and REMOVE database-incompatible fields
                            inputs = []

                            # 2. REMOVE page_range so it doesn't break LanceDB
                            for r in chunk_data:
                                inputs.append(r.pop('_embedding_input'))
                                if 'page_range' in r:
                                    r.pop('page_range') # Remove temporary worker instruction

                            # 3. Generate vectors
                            vectors = model.encode(inputs, batch_size=32, show_progress_bar=False)
                            curr_t = time.time()
                            for idx, r in enumerate(chunk_data):
                                r['vector'] = vectors[idx].tolist()
                                r['last_modified'] = curr_t

                            # 4. Save to table
                            table.add(chunk_data, mode="append")
                    else:
                        # Capture Standard Failure
                        err = msg.get('error', 'Unknown Error')
                        task_data = msg.get('task', {})

                        detailed_failures.append({
                            'filename': task_data.get('filename', 'Unknown'),
                            'path': task_data.get('file_path', 'Unknown'),
                            'error': err,
                            'action': determine_action(err),
                            'task': task_data
                        })

            except queue.Empty:
                break

        # B. SUPERVISOR CHECKS
        if time.time() - last_scale_check > 2.0:
            last_scale_check = time.time()
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            active_count = len(workers)
            current_pids = list(workers.keys())
            now = time.time()

            # --- 1. TIME-OUT KILLER ---
            for pid in current_pids:
                w_idx = worker_map.get(pid)
                state = worker_state.get(w_idx)

                # Check Timeout
                if state:
                    duration = now - state['start_time']
                    if duration > time_limit_sec:
                        fname = state['filename']
                        print(f"⏰ TIMEOUT: Worker #{w_idx} on '{fname}' (> {time_limit_sec}s)")

                        try: workers[pid].terminate()
                        except: pass

                        # LOG THE FAILURE FOR REPORT
                        detailed_failures.append({
                            'filename': fname,
                            'path': state.get('task', {}).get('file_path', 'Unknown'),
                            'error': f'Timeout (> {time_limit_sec}s)',
                            'action': determine_action('timeout'),
                            'task': state.get('task') # Captured for Phase 2 retry
                        })

                        del workers[pid]
                        spawn(w_idx)
                        completed += 1
                        dashboard.set_worker_task(w_idx, "Restarting (Timeout)...", 1)

            # --- 2. RAM SNIPER (Per-Worker Bloat) ---
            for pid in list(workers.keys()):
                try:
                    worker_mem_mb = psutil.Process(pid).memory_info().rss / (1024**2)
                    if worker_mem_mb > ram_limit_mb:
                        w_idx = worker_map.get(pid)
                        state = worker_state.get(w_idx)
                        print(f"🎯 SNIPER: Killing Worker #{w_idx} (RAM: {worker_mem_mb:.0f}MB > {ram_limit_mb}MB)")

                        workers[pid].terminate()

                        if state:
                            detailed_failures.append({
                                'filename': state['filename'],
                                'path': state.get('task', {}).get('file_path', 'Unknown'),
                                'error': f'Memory Bloat ({worker_mem_mb:.0f}MB)',
                                'action': determine_action('memory'),
                                'task': state.get('task')
                            })
                            completed += 1

                        del workers[pid]
                        spawn(worker_map.pop(pid))
                        dashboard.set_worker_task(w_idx, "Restarting (RAM)...", 1)
                except (psutil.NoSuchProcess, psutil.AccessDenied): pass

            # --- 3. CONSERVATIVE AUTO-SCALER ---
            # Added system RAM gating to prevent the 99% spikes
            if cpu < 50.0 and ram < (ram_limit_pct - 10) and active_count < max_workers:
                dashboard.add_row(current_worker_index)
                spawn(current_worker_index)
                current_worker_index += 1

        dashboard.update_global(completed, psutil.cpu_percent(), psutil.virtual_memory().percent, len(workers))
        time.sleep(0.05)

    dashboard.close()

    # Cleanup
    for _ in workers: task_queue.put(None)
    for p in workers.values(): p.join()

    return detailed_failures

def embed_documents():
    sys_conf = SETTINGS['system']
    MODEL_NAME = sys_conf['model_name']
    table = get_table()
    df = table.to_pandas()
    if df.empty: return

    all_tasks = []
    df_clean = df.drop_duplicates(subset=['file_path'], keep='first')
    processed_paths = set(df[df['vector'].apply(lambda x: x is not None and not all(v==0 for v in x))]['file_path']) if 'vector' in df.columns else set()

    standard_tasks, paginated_tasks, jumbo_tasks = [], [], []
    PAGE_SLICE, THRESHOLD = 5, 10
    JUMBO_THRESHOLD_MB = 150

    for _, row in df.drop_duplicates('file_path').iterrows():
        if row['file_path'] in processed_paths: continue

        # --- JUMBO FILE FILTER START ---
        file_path = row['file_path']
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        if file_size_mb > JUMBO_THRESHOLD_MB:
            jumbo_tasks.append(row.to_dict()) # Divert to Jumbo list
            continue
        # --- JUMBO FILE FILTER END ---
        task = row.to_dict()
        if row['file_path'].lower().endswith('.pdf'):
            pages = count_pages_fast(row['file_path'])
            if pages > THRESHOLD:
                for s in range(1, pages + 1, PAGE_SLICE):
                    p_task = task.copy()
                    p_task.update({'page_range': (s, min(s + PAGE_SLICE - 1, pages)), 'id': f"{task['id']}_p{s}"})
                    paginated_tasks.append(p_task)
                continue
        standard_tasks.append(task)

    try: model = SentenceTransformer(MODEL_NAME, device=get_best_device())
    except: model = SentenceTransformer(MODEL_NAME, device='cpu')

    # PHASE 1: Process all tasks (Standard & Paginated Slices)
    # We combine them into one large initial batch
    all_p1_tasks = standard_tasks + paginated_tasks
    f1 = run_batch_processing(all_p1_tasks, model, table, 
                            min_workers=5, max_workers=12,
                            ram_limit_mb=4000, time_limit_sec=180,
                            phase_name="Phase 1 (Standard & Slices)")

    # PHASE 2: RESCUE MISSION (Retry items that failed in Phase 1)
    # Extract only the tasks that failed but are retriable
    retry_tasks = [f['task'] for f in f1 if f.get('task')]
    timeouts_p1 = [f for f in f1 if not f.get('task')] # Items with no task data to retry

    final_failures = []
    if retry_tasks:
        print(f"\n⚠️ PHASE 2: Retrying {len(retry_tasks)} failed items with High-Resource settings...")
        # Higher RAM (6GB) and longer Timeout (5 mins) for Phase 2
        f2 = run_batch_processing(retry_tasks, model, table, 
                                min_workers=2, max_workers=4, 
                                ram_limit_mb=10000, time_limit_sec=600, 
                                phase_name="Phase 2 (Recovery)")
        final_failures = f2 + timeouts_p1
    else:
        final_failures = f1

    # PHASE 3: JUMBO FILE RECOVERY (One-by-One)
    jumbo_tasks = [t for t in all_tasks if os.path.getsize(t['file_path']) > 150 * 1024 * 1024]

    if jumbo_tasks:
        print(f"\n🐘 PHASE 3: Processing {len(jumbo_tasks)} jumbo files sequentially...")
        # 1 Worker, 12GB RAM limit, 15-minute timeout
        f3 = run_batch_processing(jumbo_tasks, model, table, 
                                min_workers=1, max_workers=1, 
                                ram_limit_mb=12000, 
                                time_limit_sec=900, 
                                phase_name="Phase 3 (Jumbo)")
        final_failures += f3

    # 4. FINAL REPORT & PERSISTENT LOGGING
    if final_failures:
        print(f"\n❌ Pipeline finished with {len(final_failures)} failures.")
        
        # Save to JSON for auditing
        log_path = "data/extraction_failures.json"
        os.makedirs("data", exist_ok=True)
        with open(log_path, "w") as f:
            log_data = [{
                "file": f.get('filename'),
                "error": f.get('error'),
                "fix": f.get('action')
            } for f in final_failures]
            json.dump(log_data, f, indent=4)
            
        # Display the final Dashboard Report
        report_dash = Dashboard(0, 0, title="Final Failure Report")
        report_dash.show_report(final_failures)
        print(f"📂 Detailed failure log saved to: {log_path}")
        # FORCE REFRESH: Small sleep to ensure UI catches up
        time.sleep(0.5) 
        input("\nPress ENTER to close report and exit...") # Manual clear-out
    else:
        print("\n✅ Pipeline Complete. All files processed successfully.")


if __name__ == "__main__":
    embed_documents()