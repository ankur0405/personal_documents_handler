import zipfile
import os
import shutil
from pathlib import Path
from .base import BaseExtractor
from src.common.utils import get_logger

logger = get_logger(__name__)

class ArchiveExtractor(BaseExtractor):
    def extract(self, file_path):
        """
        Unpacks archive for processing and yields the file manifest 
        to ensure the archive content is searchable in LanceDB.
        """
        temp_dir = Path("data/tmp") / os.path.basename(file_path)
        # Ensure a clean slate for this specific archive
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                file_list = z.namelist()
                z.extractall(temp_dir)
            
            # Yielding the file list makes the ZIP searchable by the names 
            # of the documents it contains (e.g., 'passport.jpg')
            manifest = "\n".join(file_list)
            yield 0, f"Archive contains {len(file_list)} files:\n{manifest}"
            logger.info(f"📦 Unpacked archive to {temp_dir}")
            
        except Exception as e:
            logger.error(f"❌ Archive Error {file_path}: {e}")
            yield 0, "Error: Could not unpack archive."