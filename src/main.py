import os
import glob
import lancedb
import shutil
import pyarrow as pa
import multiprocessing
import gc
import time

# Local Imports
from src.config.loader import SETTINGS
from src.agents.embedding_agent.embedder import embed_documents
from src.utils.router import process_and_route
from src.utils.schema_utils import get_arrow_schema

def scan_and_ingest():
    print("\n🔎 SCANNING: Using Centralized Schema & Router...")
    
    dimension = SETTINGS['system'].get('model_dimension', 384)
    schema = get_arrow_schema(dimension)
    
    db = lancedb.connect(SETTINGS['paths']['lancedb'])
    table_name = "documents"
    
    # Table initialization logic
    if table_name not in db.table_names():
        table = db.create_table(table_name, schema=schema)
        files_in_db = set()
    else:
        table = db.open_table(table_name)
        try:
            df = table.to_pandas()
            files_in_db = set(df['file_path'].tolist()) if not df.empty else set()
        except:
            files_in_db = set()

    raw_path = SETTINGS['paths']['raw_data']
    supported_ext_dict = SETTINGS.get('supported_extensions', {})
    extensions = [f"*{ext}" for ext in supported_ext_dict.keys()] + ["*.zip"]
    
    files_on_disk = []
    for ext in extensions:
        files_on_disk.extend(glob.glob(os.path.join(raw_path, "**", ext), recursive=True))

    new_records = []
    for f_path in files_on_disk:
        records = process_and_route(f_path, dimension, files_in_db)
        new_records.extend(records)
        
        # Batch DB ingestion to save RAM
        if len(new_records) >= 100:
            table.add(new_records)
            new_records = []
            gc.collect()

    if new_records:
        table.add(new_records)
    print("   ✅ Ingestion Sync Complete.")

def main():
    # macOS Start Method Fix
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass

    os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"
    
    scan_and_ingest()
    
    # Cooldown for RAM reclamation
    gc.collect()
    time.sleep(2)
    
    embed_documents()
    
    # Optional Global Cleanup
    should_cleanup = SETTINGS.get('system', {}).get('cleanup_temp', True)
    temp_path = os.path.join(os.getcwd(), "test_temp")
    if should_cleanup and os.path.exists(temp_path):
        print(f"\n🧹 CLEANUP: Removing {temp_path}")
        shutil.rmtree(temp_path)

if __name__ == "__main__":
    main()