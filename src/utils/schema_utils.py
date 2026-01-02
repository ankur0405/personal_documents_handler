import os
import uuid
import json
import pyarrow as pa
from datetime import datetime

# THE BLUEPRINT: Update this list to add any missing fields (like issue_date)
SCHEMA_FIELDS = [
    ("id", pa.string()),
    ("file_path", pa.string()),
    ("filename", pa.string()),
    ("file_type", pa.string()),
    ("created_at", pa.string()),
    ("category", pa.string()),
    ("processing_status", pa.string()),
    ("page_number", pa.int32()),
    ("content", pa.string()),
    ("issue_date", pa.string()),
    ("expiry_date", pa.string()),
    ("primary_date", pa.string()),
    ("country", pa.string()),
    ("person", pa.string()),
    ("summary", pa.string()),
    ("metadata", pa.string()),
    ("last_modified", pa.float64())
]

def get_arrow_schema(dimension):
    """Generates the LanceDB schema including the vector column."""
    fields = [pa.field(name, dtype) for name, dtype in SCHEMA_FIELDS]
    fields.append(pa.field("vector", pa.list_(pa.float32(), dimension)))
    return pa.schema(fields)

def get_default_record(f_path, dimension):
    """Generates a dictionary matching the schema for initial ingestion."""
    return {
        "id": str(uuid.uuid4()),
        "file_path": os.path.normpath(f_path),
        "filename": os.path.basename(f_path),
        "file_type": os.path.splitext(f_path)[1].lower(),
        "created_at": datetime.now().isoformat(),
        "vector": [0.0] * dimension,
        "category": "Uncategorized",
        "processing_status": "pending",
        "page_number": 0,
        "content": "",
        "issue_date": "",
        "expiry_date": "",
        "primary_date": "",
        "country": "", # Initialize missing fields
        "person": "",
        "summary": "",
        "metadata": json.dumps({}),
        "last_modified": 0.0
    }