import sys
import os
import pandas as pd

# Fix path to allow importing from src
sys.path.append(os.getcwd())

from src.common.db import get_table

def force_clean_duplicates():
    print("--- 🧹 AGGRESSIVE DATABASE CLEANER ---")
    
    table = get_table()
    df = table.to_pandas()
    
    if df.empty:
        print("⚠️ Database is empty.")
        return

    print(f"📊 Current Total Rows: {len(df)}")
    
    # 1. Deduplicate by ID
    # If two files have the same ID (Content Hash), we keep the FIRST one and drop the rest.
    # This removes both "True Duplicates" and "Renamed Copies".
    df_clean = df.drop_duplicates(subset=['id'], keep='first')
    
    duplicates_removed = len(df) - len(df_clean)
    
    if duplicates_removed == 0:
        print("✅ No duplicates found based on ID.")
        return

    print(f"🔥 Found {duplicates_removed} conflicting IDs.")
    print("   (This includes identical files saved with different names)")

    # 2. The Nuclear Reset
    # We wipe the table completely and re-insert ONLY the unique rows.
    print("DATA OPERATION: Wiping table and re-inserting unique records...")
    
    try:
        table.delete("true") # Deletes everything
        table.add(df_clean.to_dict('records'))
        print(f"✅ Success! Database now contains {len(df_clean)} unique records.")
        
    except Exception as e:
        print(f"❌ Critical Error during wipe/insert: {e}")

if __name__ == "__main__":
    force_clean_duplicates()