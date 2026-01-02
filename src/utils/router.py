import os
import zipfile
import uuid
from src.config.loader import SETTINGS
from src.utils.schema_utils import get_default_record

def process_and_route(file_path, dimension, files_in_db):
    ext = os.path.splitext(file_path)[1].lower()
    supported_exts = SETTINGS.get('supported_extensions', {})
    new_records = []

    # Automated creation of the test_temp folder
    base_temp_dir = os.path.join(os.getcwd(), "test_temp")
    os.makedirs(base_temp_dir, exist_ok=True)

    if ext == ".zip":
        # Create unique subfolder for this zip
        temp_dir = os.path.join(base_temp_dir, f"extract_{uuid.uuid4().hex[:6]}")
        os.makedirs(temp_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                z.extractall(temp_dir)
                for root, _, files in os.walk(temp_dir):
                    for f in files:
                        child_path = os.path.normpath(os.path.join(root, f))
                        if os.path.splitext(f)[1].lower() in supported_exts:
                            if child_path not in files_in_db:
                                new_records.append(get_default_record(child_path, dimension))
        except Exception as e:
            print(f"⚠️ Zip Error: {e}")
        return new_records

    elif ext in supported_exts and os.path.normpath(file_path) not in files_in_db:
        new_records.append(get_default_record(file_path, dimension))
            
    return new_records