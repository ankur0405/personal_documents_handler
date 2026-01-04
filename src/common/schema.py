import pyarrow as pa
from src.config.loader import config

# Central Enterprise Schema: Synchronized with db.py
DOCUMENT_SCHEMA = pa.schema([
    pa.field("id", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), config.model_dimension)),
    pa.field("filename", pa.string()),
    pa.field("file_path", pa.string()),
    pa.field("file_type", pa.string()),
    pa.field("content", pa.string(), nullable=True),
    pa.field("tags", pa.list_(pa.string())),
    pa.field("source", pa.string()),
    pa.field("engine_version", pa.string()),
    pa.field("timestamp", pa.string()),
    pa.field("created_at", pa.string()),
    pa.field("category", pa.string()),
    pa.field("processing_status", pa.string()),
    pa.field("page_number", pa.int32()),
    pa.field("last_modified", pa.float64()),
    pa.field("issue_date", pa.string()),
    pa.field("expiry_date", pa.string()),
    pa.field("primary_date", pa.string()),
    pa.field("country", pa.string()),
    pa.field("person", pa.string())
])


def sanitize_for_db(record: dict):
    """
    Enterprise Guardrail:
    Ensures the dictionary contains only fields defined in the PyArrow schema
    and provides defaults for missing non-nullable fields.
    """
    allowed_keys = set(DOCUMENT_SCHEMA.names)

    # 1. Strip extra processing fields (like _embedding_input)
    clean_record = {k: v for k, v in record.items() if k in allowed_keys}

    # 2. Fill missing mandatory fields with defaults to
    # prevent Arrow Invalid errors
    if "tags" not in clean_record:
        clean_record["tags"] = []
    if "page_number" not in clean_record:
        clean_record["page_number"] = 1

    return clean_record
