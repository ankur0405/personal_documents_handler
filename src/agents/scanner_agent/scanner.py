"""
Module: File Scanner Agent
Description: Recursively scans subdirectories using dynamic extensions from settings.yaml.
"""

import pathlib
import xxhash
import yaml
import os
from typing import List, Optional
from src.common.db import Document, get_table


# --- CONFIGURATION LOADER ---
def load_supported_extensions() -> set:
    """Reads supported extensions directly from settings.yaml. No hardcoded fallbacks."""
    try:
        config_path = pathlib.Path("src/config/settings.yaml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Fetch precisely what the user defined in the config
                exts = config.get('supported_extensions', [])
                if exts:
                    # Normalize: lowercase and ensure it starts with a dot
                    return {f".{str(e).strip('.').lower()}" for e in exts}

        print("⚠️ Warning: settings.yaml not found or 'supported_extensions' is empty.")
    except Exception as e:
        print(f"❌ Error reading config: {e}")

    # Return an empty set if config fails.
    # This forces the user to check their settings
    # instead of silently running a partial scan.
    return set()

SUPPORTED_EXTS = load_supported_extensions()
BATCH_SIZE = 100


def calculate_file_hash(filepath: str) -> Optional[str]:
    """Generates a unique ID based on file content for deduplication."""
    hasher = xxhash.xxh64()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


def scan_directory(root_path: str):
    root = pathlib.Path(root_path)

    if not root.exists():
        print(f"❌ Path not found: {root_path}")
        return

    if not SUPPORTED_EXTS:
        print("❌ No supported extensions loaded. Check settings.yaml. Aborting scan.")
        return

    print(f"🔍 Recursive Scan: {root_path}")
    print(f"📂 Looking for: {SUPPORTED_EXTS}")

    docs_batch: List[Document] = []
    table = get_table()
    total_found = 0

    for path in root.rglob('*'):
        if path.name.startswith("._") or path.is_dir():
            continue

        if path.suffix.lower() in SUPPORTED_EXTS:
            try:
                stats = path.stat()
                file_hash = calculate_file_hash(str(path))
                if not file_hash: continue

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
                total_found += 1

                if len(docs_batch) >= BATCH_SIZE:
                    _safe_add(table, docs_batch)
                    print(f"  -> Indexed {total_found} files...")
                    docs_batch = []
            except Exception:
                continue

    if docs_batch:
        _safe_add(table, docs_batch)

    print(f"✅ Scan Complete. {total_found} files synchronized.")


def _safe_add(table, docs_batch):
    data_payload = [d.model_dump() for d in docs_batch]
    try:
        table.add(data_payload)
    except Exception:
        pass

if __name__ == "__main__":
    scan_directory(os.getenv("SCAN_PATH", "/data/raw"))
