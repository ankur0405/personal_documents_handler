"""
Module: File Scanner Agent (Debug Mode)
Description: Uses simple 'table.add()' to force data writing.
"""

import pathlib
import xxhash
from typing import List, Optional
from src.common.db import Document, get_table

# --- CONFIGURATION ---
SUPPORTED_EXTS = {
    # Documents
    '.pdf', '.docx', '.doc', '.txt', '.md', '.rtf',
    # Spreadsheets
    '.xls', '.xlsx', '.csv',
    # Slides
    '.pptx', '.ppt',
    # Images (Metadata/Filename only for now, unless we add OCR)
    '.png', '.jpg', '.jpeg', '.heic',
    # Web/Code
    '.html', '.json', '.xml',
    '.msg'
}
BATCH_SIZE = 100

def calculate_file_hash(filepath: str) -> Optional[str]:
    hasher = xxhash.xxh64()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"⚠️  Error hashing {filepath}: {e}")
        return None

def scan_directory(root_path: str):
    root = pathlib.Path(root_path)
    
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root_path}")

    print(f"🔍 Scanning Target: {root_path}")
    
    docs_batch: List[Document] = []
    table = get_table()
    
    # DEBUG: Print the DB Path to ensure we are looking at the same file
    print(f"📂 Connected to Table: {table.name}")
    
    for path in root.rglob('*'):
        if path.name.startswith("._"):
            continue
            
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            stats = path.stat()
            file_hash = calculate_file_hash(str(path))
            
            if not file_hash: 
                continue

            doc = Document(
                id=file_hash,
                filename=path.name,
                file_path=str(path.absolute()),
                file_type=path.suffix.lower().strip('.'),
                file_size_bytes=stats.st_size,
                creation_date=stats.st_ctime,
                last_modified=stats.st_mtime,
                summary="",
                category="Unsorted"
            )
            docs_batch.append(doc)

            if len(docs_batch) >= BATCH_SIZE:
                # FIX: Use 'add' instead of 'merge_insert'.
                # 'add' is the simplest way to write data. It crashes on duplicates,
                # but since we are starting fresh, it GUARANTEES writing.
                data_payload = [d.model_dump() for d in docs_batch]
                table.add(data_payload) # <--- CHANGED THIS
                
                print(f"  -> Processed batch of {len(docs_batch)} files...")
                docs_batch = [] 

    if docs_batch:
        data_payload = [d.model_dump() for d in docs_batch]
        table.add(data_payload) # <--- CHANGED THIS
        print(f"  -> Processed final batch of {len(docs_batch)} files...")

    print("✅ Scan Complete. Database is synchronized.")