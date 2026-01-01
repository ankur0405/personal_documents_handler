import lancedb
from lancedb.pydantic import LanceModel, Vector
from typing import Optional
from pydantic import Field # Standard Pydantic Field

from src.config.loader import SETTINGS

# 1. Load Settings
DB_PATH = SETTINGS['paths']['db_path']
DIMENSION = SETTINGS['system']['model_dimension']

# 2. Define the Schema
class Document(LanceModel):
    # IDs
    id: str
    
    # THE FIX: We make vector required in the Schema, but provide a default 
    # generator. If Scanner doesn't provide one, this fills it with 0.0s.
    vector: Vector(DIMENSION) = Field(default_factory=lambda: [0.0] * DIMENSION)
    
    # Default content to empty string so Scanner doesn't fail
    content: str = Field(default="")
    page_number: int = Field(default=1)
    
    # Metadata (Required)
    filename: str
    file_path: str
    last_modified: float
    
    # --- INTELLIGENT FIELDS (Optional) ---
    category: Optional[str] = "uncategorized"
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    country: Optional[str] = None
    person: Optional[str] = None
    summary: Optional[str] = None

# 3. Singleton Database Connection
_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = lancedb.connect(DB_PATH)
    return _db_instance

def get_table(table_name="documents"):
    db = get_db()
    return db.create_table(table_name, schema=Document, exist_ok=True)