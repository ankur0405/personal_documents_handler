"""
Module: File Scanner Agent
Description: Recursively scans a local directory, calculates distinct content hashes,
and synchronizes the metadata with the LanceDB vector store.

Key Features:
- Ignores macOS 'AppleDouble' (._) hidden files to prevent duplicates.
- Uses xxHash for extremely fast, low-collision checksums.
- Implements 'Upsert' logic (merge_insert) to handle re-scans gracefully.
"""

import pathlib
import xxhash
from typing import List, Optional
from src.common.db import Document, get_table

# --- CONFIGURATION ---
# Allowed file extensions. We filter strictly to avoid indexing system files or binaries.
SUPPORTED_EXTS = {'.pdf', '.docx', '.txt', '.md', '.png', '.jpg', '.jpeg', '.xls', '.xlsx'}

# Batch size controls memory usage vs. disk I/O.
# 100 is a safe sweet spot for SQLite/LanceDB inserts.
BATCH_SIZE = 100

def calculate_file_hash(filepath: str) -> Optional[str]:
    """
    Generates a unique xxHash64 ID for the file content.

    Args:
        filepath (str): Absolute path to the file.

    Returns:
        str: Hex digest of the hash, or None if reading failed.

    Why xxHash?
    It is significantly faster than MD5/SHA256 (RAM speed limits) and has an
    extremely low collision rate. Perfect for local file systems.
    """
    hasher = xxhash.xxh64()
    try:
        # Open in binary mode ('rb').
        # We read in 8KB chunks to ensure we never load a 5GB video file
        # entirely into RAM, avoiding memory crashes.
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        # Common errors: PermissionDenied, FileLocked, or File Corrupted.
        # We log and skip rather than crashing the whole scan.
        print(f"⚠️  Error hashing {filepath}: {e}")
        return None

def scan_directory(root_path: str):
    """
    Main Execution Loop:
    1. Walks the directory tree.
    2. Filters junk files (macOS metadata).
    3. Hashes valid files.
    4. Upserts metadata to Database.

    Args:
        root_path (str): The folder path to start scanning from.
    """
    root = pathlib.Path(root_path)

    # Validation: Fail early if the path is invalid.
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root_path}")

    print(f"🔍 Scanning Target: {root_path}")

    docs_batch: List[Document] = []
    table = get_table() # Connect to DB

    # rglob('*') is a generator that recursively yields all files in subfolders.
    # It is memory efficient compared to loading all paths into a list.
    for path in root.rglob('*'):

        # --- FILTER 1: macOS Metadata (The Duplicate Fix) ---
        # macOS creates hidden files starting with '._' on non-native drives (USB/Network).
        # These contain resource forks (thumbnails/metadata) but share the same binary header,
        # leading to duplicate hashes. We MUST ignore them.
        if path.name.startswith("._"):
            continue

        # --- FILTER 2: Valid File Types ---
        # strictly check extension to ignore system junk (.DS_Store, .tmp, etc)
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:

            # 1. Gather Metadata (Fast OS call)
            stats = path.stat()

            # 2. Calculate Identity (Content Hash)
            # This is the most expensive operation (IO bound).
            file_hash = calculate_file_hash(str(path))

            # Skip if hashing failed (permission error)
            if not file_hash:
                continue

            # 3. Create Data Model
            # Pydantic validates data types here (e.g., ensuring size is an int)
            doc = Document(
                id=file_hash, # PRIMARY KEY
                filename=path.name,
                file_path=str(path.absolute()),
                file_type=path.suffix.lower().strip('.'),
                file_size_bytes=stats.st_size,
                creation_date=stats.st_ctime,
                last_modified=stats.st_mtime,
                summary="",       # Placeholder for Phase 2
                category="Unsorted" # Placeholder for Phase 3
            )
            docs_batch.append(doc)

            # --- BATCH INSERTION ---
            # Writing to disk is slow. We accumulate 100 records and write once.
            if len(docs_batch) >= BATCH_SIZE:
                # merge_insert is critical for Idempotency (safe re-runs).
                # It acts as an UPSERT:
                # - If 'id' exists: Update the row.
                # - If 'id' is new: Insert the row.
                table.merge_insert(docs_batch)

                print(f"  -> Processed batch of {len(docs_batch)} files...")
                docs_batch = [] # Clear memory

    # --- FINAL FLUSH ---
    # Process any remaining files in the buffer (e.g., last 42 files).
    if docs_batch:
        table.merge_insert(docs_batch)
        print(f"  -> Processed final batch of {len(docs_batch)} files...")

    print("✅ Scan Complete. Database is synchronized.")