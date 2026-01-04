import os
import time
import torch
import multiprocessing
import queue
from sentence_transformers import SentenceTransformer

# Standardized Imports
from src.common.db import DatabaseManager
from src.config.loader import config
from src.config.autotune import get_hardware_profile # Use the tuner directly [cite: 6]
from src.agents.embedding_agent.dashboard import Dashboard
from src.agents.embedding_agent.worker import worker_entrypoint

def run_batch_processing(tasks, model, table, profile, phase_name="Main"):
    """
    Core execution engine using the validated hardware profile. [cite: 77, 78]
    Uses a Sentinel approach to ensure all processes terminate cleanly. [cite: 78]
    """
    if not tasks:
        return []

    # Identify worker count from the auto-tuned profile [cite: 9]
    min_workers = profile.get('max_workers', 4)
    dashboard = Dashboard(len(tasks), min_workers, title=f"Pipeline: {phase_name}")

    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    workers = {}

    def spawn(idx):
        # Uses 'spawn' method for macOS compatibility [cite: 151, 157]
        p = multiprocessing.Process(target=worker_entrypoint, args=(task_queue, result_queue, idx))
        p.daemon = True
        p.start()
        workers[p.pid] = p
        return p

    print(f"\n🚀 {phase_name}: {len(tasks)} files | Concurrency: {min_workers} Workers")

    # Initialize worker pool based on Auto-Tune [cite: 10]
    for i in range(min_workers):
        spawn(i)

    # Load tasks into the queue
    for t in tasks:
        task_queue.put(t)

    # SENTINEL: Put a None signal for each worker to ensure graceful shutdown [cite: 22, 79]
    for _ in range(min_workers + 2):
        task_queue.put(None)

    completed = 0
    total = len(tasks)

    while completed < total:
        try:
            # Non-blocking result retrieval [cite: 80]
            msg = result_queue.get(timeout=1.0)
            
            if msg['type'] == 'DONE':
                completed += 1
                if msg['success']:
                    chunk_data = msg['data']
                    
                    # PERFORMANCE: Batch vectorize on main process to utilize MPS GPU [cite: 81, 82]
                    inputs = [r.pop('_embedding_input') for r in chunk_data]
                    vectors = model.encode(inputs, batch_size=32, show_progress_bar=False)

                    for idx, r in enumerate(chunk_data):
                        r['vector'] = vectors[idx].tolist()
                        r['last_modified'] = time.time()

                    # Commit cleaned batch to LanceDB [cite: 48, 83]
                    table.add(chunk_data)
                    
                    # Update the Tkinter Dashboard UI [cite: 75, 83]
                    if hasattr(dashboard, 'update_global'):
                        dashboard.update_global()
                else:
                    print(f"❌ Failed task: {msg.get('filename')} - {msg.get('error')}")
                    
        except queue.Empty:
            continue

    # FINAL CLEANUP: Explicitly join processes to reclaim all RAM [cite: 85]
    for p in workers.values():
        p.join(timeout=1.0)
        if p.is_alive():
            p.terminate()

    return []

def embed_documents():
    """
    Orchestrates the intelligence layer using auto-tuned settings. [cite: 86]
    """
    print("\n--- 🧠 STARTING INTELLIGENCE LAYER ---")

    # Get tuned profile for your 64GB Mac (MPS support) [cite: 7, 8]
    profile = get_hardware_profile()

    # Initialize model on the detected device (mps or cpu) [cite: 8, 87]
    model = SentenceTransformer(config.model_name, device=profile['device'])
    
    db_manager = DatabaseManager()
    table = db_manager.initialize_table()

    # Fetch Tasks from standardized table [cite: 87, 88]
    df_all = table.to_pandas()
    if df_all.empty:
        print("⚠️ Database is empty. Please run the Scanner first.")
        return

    # Check for empty content string OR null records [cite: 88]
    tasks = df_all[(df_all['content'].isna()) | (df_all['content'] == "")].to_dict('records')

    if not tasks:
        print("✅ All documents are already vectorized. No new work found.")
        return

    # Run processing with tuned profile [cite: 89, 90]
    run_batch_processing(tasks, model, table, profile, phase_name="Smoke Test")