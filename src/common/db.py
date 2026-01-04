import lancedb
import pyarrow as pa
from pathlib import Path
from src.config.loader import config

class DatabaseManager:
    def __init__(self, db_path=None):
        path = db_path or config.db_path
        self.db_path = Path(path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.db_path))

    def initialize_table(self):
        """Strict Arrow schema matching the full suite of extraction fields."""
        schema = pa.schema([
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

        table_name = "document_intel"
        if table_name not in self.db.table_names():
            return self.db.create_table(table_name, schema=schema)
        return self.db.open_table(table_name)