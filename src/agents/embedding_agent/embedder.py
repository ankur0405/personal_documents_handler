import time
import psutil
import torch
import multiprocessing
import queue
from sentence_transformers import SentenceTransformer

# Local Imports
from src.common.db import get_table
from src.config.loader import SETTINGS
from src.agents.embedding_agent.dashboard import Dashboard
from src.agents.embedding_agent.worker import worker_entrypoint

def get_best_device():
    if torch.cuda.is_available(): return 'cuda'
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available(): return 'mps'
    return 'cpu'

def run_batch_processing(tasks, model, table, min_workers=5, max_workers=12, ram_limit_mb=4000, phase_name="Main"):
    if not tasks: return []
    
    # 1. INIT UI
    dashboard = Dashboard(len(tasks), min_workers, title=f"Pipeline: {phase_name}")
    
    # 2. INIT QUEUES
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    workers = {}    
    worker_map = {} 
    failed_tasks = []
    
    # 3. SPAWN INITIAL WORKERS
    def spawn(idx):
        p = multiprocessing.Process(target=worker_entrypoint, args=(task_queue, result_queue, idx))
        p.start()
        workers[p.pid] = p
        worker_map[p.pid] = idx
        return p

    print(f"\n🚀 {phase_name}: {len(tasks)} files | Auto-Scale: {min_workers}-{max_workers} Workers")
    for i in range(min_workers): spawn(i)
    
    current_worker_index = min_workers

    # Feed Tasks
    for t in tasks: task_queue.put(t)

    # 4. MAIN LOOP
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
                    # Set text and max progress
                    dashboard.set_worker_task(w_idx, msg['filename'], msg['total'])
                    
                elif msg['type'] == 'PROGRESS':
                    # Update ONLY the bar
                    dashboard.update_worker_progress(w_idx, msg['current'])
                    
                elif msg['type'] == 'DONE':
                    completed += 1
                    dashboard.set_worker_task(w_idx, "Idle", 1) # Reset text
                    dashboard.update_worker_progress(w_idx, 0)  # Reset bar
                    
                    if msg['success']:
                        chunk_data = msg['data']
                        if chunk_data:
                            inputs = [c.pop('_embedding_input') for c in chunk_data]
                            vectors = model.encode(inputs, batch_size=32, show_progress_bar=False)
                            curr_t = time.time()
                            for idx, r in enumerate(chunk_data):
                                r['vector'] = vectors[idx].tolist()
                                r['last_modified'] = curr_t
                            table.add(chunk_data, mode="append")
                    else:
                        if 'task' in msg: failed_tasks.append(msg['task'])
                        
            except queue.Empty:
                break

        # B. AUTO-SCALER (Checks every 2s)
        if time.time() - last_scale_check > 2.0:
            last_scale_check = time.time()
            
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            active_count = len(workers)
            
            # Scale Up
            if cpu < 50.0 and ram < 60.0 and active_count < max_workers:
                dashboard.add_row(current_worker_index)
                spawn(current_worker_index)
                print(f"   ⚡ Scaling Up: Spawning Worker #{current_worker_index}")
                current_worker_index += 1

            # Sniper
            current_pids = list(workers.keys())
            for pid in current_pids:
                try:
                    proc = psutil.Process(pid)
                    mem_mb = proc.memory_info().rss / (1024 * 1024)
                    
                    if mem_mb > ram_limit_mb:
                        workers[pid].terminate()
                        del workers[pid]
                        row_idx = worker_map.pop(pid)
                        spawn(row_idx)
                        
                except psutil.NoSuchProcess:
                    if pid in workers:
                        row_idx = worker_map.pop(pid)
                        del workers[pid]
                        spawn(row_idx)

        # C. Update Global Stats
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        dashboard.update_global(completed, cpu, ram, len(workers))
        
        time.sleep(0.05)

    dashboard.close()
    
    # Cleanup
    for _ in workers: task_queue.put(None)
    for p in workers.values(): p.join()
    
    return failed_tasks

def embed_documents():
    sys_conf = SETTINGS['system']
    MODEL_NAME = sys_conf['model_name']
    
    table = get_table()
    df = table.to_pandas()
    if df.empty: return

    all_tasks = []
    df_clean = df.drop_duplicates(subset=['file_path'], keep='first')
    for _, row in df_clean.iterrows():
         if 'vector' not in row or row['vector'] is None:
             all_tasks.append(row.to_dict())
         elif hasattr(row['vector'], '__len__') and all(v==0.0 for v in row['vector']):
             all_tasks.append(row.to_dict())

    if not all_tasks:
        print("✅ System Synced.")
        return

    try: model = SentenceTransformer(MODEL_NAME, device=get_best_device())
    except: model = SentenceTransformer(MODEL_NAME, device='cpu')
    
    failures = run_batch_processing(all_tasks, model, table, 
                                    min_workers=5, max_workers=12, 
                                    ram_limit_mb=4000, phase_name="Phase 1")

    if failures:
        print(f"\n⚠️  Retrying {len(failures)} failed files...")
        run_batch_processing(failures, model, table, 
                             min_workers=1, max_workers=2, 
                             ram_limit_mb=8000, phase_name="Phase 2")
            
    print("\n✅ Pipeline Complete.")

if __name__ == "__main__":
    embed_documents()