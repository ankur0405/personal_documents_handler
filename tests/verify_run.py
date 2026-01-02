import lancedb
import pandas as pd
import json
import os
from src.config.loader import SETTINGS

def verify_data():
    print("\n📊 DATA AUDIT")
    db = lancedb.connect(SETTINGS['paths']['lancedb'])
    if "documents" not in db.table_names(): return print("❌ No table found.")
    
    df = db.open_table("documents").to_pandas()
    print(f"✅ Total records: {len(df)}")
    print(f"⚠️  Missing Dates: {len(df[df['issue_date'] == ''])}")
    print(f"⚠️  Null Vectors: {len(df[df['vector'].apply(lambda x: all(v==0 for v in x))])}")

    if os.path.exists("data/extraction_failures.json"):
        with open("data/extraction_failures.json", "r") as f:
            print(f"❌ Final Failures: {len(json.load(f))}")

if __name__ == "__main__": verify_data()