import os
from pathlib import Path
import lancedb
import pandas as pd

# 1. Use the EXACT string from your printf output
DATA_PATH = Path("/Users/ankur/Tech/Python/personnal_documents_handler/data/raw")
DB_PATH = Path("/Users/ankur/Tech/Python/personnal_documents_handler/data/lancedb_store")

print(f"🔍 Probing Path: {DATA_PATH}")

# 2. Check existence AND readability
if not DATA_PATH.exists():
    print(f"❌ OS says this path does NOT exist.")
    # Debug: check the parent folder
    if DATA_PATH.parent.exists():
        print(f"📁 Parent folder exists. Contents of {DATA_PATH.parent}:")
        print([p.name for p in DATA_PATH.parent.iterdir()])
    exit()

if not os.access(DATA_PATH, os.R_OK):
    print(f"🚫 PERMISSION DENIED: Python cannot read this folder.")
    print("Go to System Settings > Privacy > Full Disk Access and add your Terminal/Python.")
    exit()

# 3. Connect to Database
db = lancedb.connect(str(DB_PATH))
table = db.open_table('documents')

# 2. Get all vectorized files using the correct column name 'filename'
df_db = table.to_pandas()
vectorized_files = set(df_db['filename'].unique()) if 'filename' in df_db.columns else set()

report_data = []
valid_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.xlsx')

# 3. Defensive Scan
if not os.path.exists(DATA_PATH):
    print(f"❌ ERROR: DATA_PATH does not exist: {DATA_PATH}")
else:
    for root, dirs, files in os.walk(DATA_PATH):
        for file in files:
            # Skip hidden files like .DS_Store
            if file.startswith('.'): continue
            
            status = "Vectorized" if file in vectorized_files else "Skipped/Failed"
            reason = "Success"
            if status == "Skipped/Failed":
                reason = "Unsupported Extension" if not file.lower().endswith(valid_extensions) else "Pending OCR"
            
            report_data.append({"File": file, "Status": status, "Reason": reason})

# 4. Final Reporting with "Empty" Check
report_df = pd.DataFrame(report_data)

if report_df.empty:
    print("⚠️ No files were found in the provided DATA_PATH.")
else:
    print("\n--- Processing Summary ---")
    if 'Status' in report_df.columns:
        print(report_df['Status'].value_counts())
    
    report_df.to_csv("vectorization_report_v2.csv", index=False)
    print("\n✅ Report saved to vectorization_report_v2.csv")