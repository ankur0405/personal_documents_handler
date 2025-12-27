import sys
import os
import pandas as pd

# --- PATH SETUP ---
# We need to see 'src'.
# Since this file is in 'personnal_documents_handler/tests/',
# going up one level ('..') takes us to the Project Root.
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.common.db import get_table

def inspect_database():
    print("--- 🕵️‍♂️ Starting Database Inspection ---")

    try:
        table = get_table()
        df = table.to_pandas()
    except Exception as e:
        print(f"❌ Error connecting to DB: {e}")
        return

    # Basic Stats
    total_rows = len(df)
    unique_ids = df['id'].nunique()

    print(f"📊 Total Documents: {total_rows}")
    print(f"🔑 Unique IDs:      {unique_ids}")

    # Validation Logic
    if total_rows == unique_ids:
        print("\n✅ INTEGRITY CHECK PASSED: No duplicate IDs found.")
    else:
        print(f"\n❌ WARNING: Found {total_rows - unique_ids} duplicate records!")
        print(df[df.duplicated(subset=['id'], keep=False)][['filename', 'id']])

    print("\n--- 📄 First 5 Records ---")
    print(df[['filename', 'file_type', 'file_size_bytes']].head().to_string())

if __name__ == "__main__":
    inspect_database()