import lancedb
from src.config.loader import SETTINGS
from src.utils.schema_utils import get_arrow_schema # Import centralized blueprint

DB_PATH = SETTINGS['paths']['lancedb']
DIMENSION = SETTINGS['system']['model_dimension']

def get_db():
    return lancedb.connect(DB_PATH)

def get_table(table_name="documents"):
    db = get_db()
    
    # Use the centralized schema so it matches main.py and router.py
    schema = get_arrow_schema(DIMENSION)
    
    if table_name in db.table_names():
        return db.open_table(table_name)
    else:
        # First run: create it with the explicit blueprint
        return db.create_table(table_name, schema=schema)