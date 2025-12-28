import lancedb
import os
from lancedb.pydantic import LanceModel, Vector
from pydantic import Field
from pathlib import Path
from src.config.loader import SETTINGS

# --- CONFIGURATION ---
# Dynamically resolve the project root to ensure this works
# regardless of where the script is called from.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Construct the absolute path using the relative path from settings.yaml
# Config says "data/lancedb_store", so we join it with the project root.
DB_PATH = os.path.join(BASE_DIR, SETTINGS['paths']['db_path'])

# Ensure the data directory exists before we try to connect
os.makedirs(DB_PATH, exist_ok=True)

# --- DYNAMIC SCHEMA CONFIG ---
# This is the key fix. We read the dimension (768 or 384) from the config.
VECTOR_DIM = SETTINGS['system']['model_dimension']
print(f"🔌 Database Schema Configured for: {VECTOR_DIM} dimensions")

# --- SCHEMA DEFINITION ---
class Document(LanceModel):
    """
    The Master Schema for our Document Database.
    Inherits from LanceModel to allow seamless integration with LanceDB.
    """
    # Primary Key: Unique ID (usually file_hash + page_num)
    id: str = Field(pk=True)

    # Metadata Fields
    filename: str
    file_path: str
    file_type: str
    file_size_bytes: int
    creation_date: float = Field(default=0.0)
    last_modified: float = Field(default=0.0)

    # --- AI FIELDS ---
    page_number: int = Field(default=1)
    content: str = Field(default="")

    # DYNAMIC VECTOR SIZE
    # We use the variable from config instead of hardcoded 384.
    # We also update the default zero-vector to match this size.
    vector: Vector(VECTOR_DIM) = Field(default=[0.0] * VECTOR_DIM)

    # Future-proofing fields (Phase 2/3)
    summary: str = Field(default="")
    category: str = Field(default="Unsorted")


# --- DATABASE CONNECTION ---
def get_table(table_name="documents"):
    """
    Connects to the embedded LanceDB instance and retrieves the requested table.
    Safely creates the table if it does not exist.
    """
    db = lancedb.connect(DB_PATH)

    if table_name in db.table_names():
        return db.open_table(table_name)
    else:
        # Create a new table using the Dynamic Schema defined above
        return db.create_table(table_name, schema=Document)