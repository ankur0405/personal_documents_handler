import zipfile
import os
from pathlib import Path
from .base import BaseExtractor

class ArchiveExtractor(BaseExtractor):
    def extract(self, file_path):
        temp_dir = Path("data/tmp") / os.path.basename(file_path)
        temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                z.extractall(temp_dir)
            yield 0, f"ARCHIVE_UNPACKED: {temp_dir}"
        except Exception:
            pass