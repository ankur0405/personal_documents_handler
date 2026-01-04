import os
from src.config.loader import config
from src.utils.schema_utils import get_default_record

def process_and_route(file_path, dimension, files_in_db):
    """
    Standardizes routing and ensures all 6 smoke-test files are registered.
    """
    ext = os.path.splitext(file_path)[1].lower()
    # Normalize extensions to ensure matching
    supported_exts = {e.lower() for e in getattr(config, 'supported_extensions', {}).keys()}
    new_records = []

    norm_path = os.path.normpath(file_path)

    # Allow anything in settings.yaml plus .zip
    if ext in supported_exts or ext == ".zip":
        if norm_path not in files_in_db:
            record = get_default_record(norm_path, dimension)
            
            # Flatten to match LanceDB schema (No nested dicts)
            record.pop("metadata", None)
            record.pop("summary", None)
            record["source"] = "extreme_ssd"
            record["engine_version"] = "2.0"
            record["tags"] = []
            record["timestamp"] = record.get("created_at")
            
            new_records.append(record)

    return new_records