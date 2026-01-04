import lancedb
import pandas as pd
import numpy as np
import sys
import os

# Ensure the project root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.loader import config

def audit_sink():
    print("🚀 Starting Enterprise Sink Quality Audit...")
    db = lancedb.connect(config.db_path)
    table = db.open_table("document_intel")
    df = table.to_pandas()

    print(f"\n--- 📊 DATA INTEGRITY REPORT ---")
    print(f"✅ Total Records: {len(df)}")
    
    # 1. Content Check
    empty = df[df['content'].fillna('').str.strip().str.len() == 0]
    if not empty.empty:
        print(f"⚠️  WARNING: {len(empty)} records have empty content: {empty['filename'].tolist()}")

    # 2. FTS Repair & Search Test
    print(f"\n--- 🔎 SEARCH CAPABILITY ---")
    try:
        # Create index if search fails
        print("🛠️  Ensuring FTS Index is initialized...")
        table.create_fts_index("content", replace=True) 
        
        # Test Keyword Search
        keyword_results = table.search("Benefits").limit(1).to_pandas()
        if not keyword_results.empty:
            print(f"✅ FTS Search: Functional (Found: {keyword_results.iloc[0]['filename']})")
        else:
            print("⚠️  FTS Search: Index created, but keyword 'Benefits' not found in content.")
            
    except Exception as e:
        print(f"❌ Search Test Failed: {e}")

if __name__ == "__main__":
    audit_sink()