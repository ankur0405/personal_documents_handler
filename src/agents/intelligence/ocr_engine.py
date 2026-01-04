import os
import cv2
import importlib
from datetime import datetime
from pathlib import Path
from src.config.loader import config
from src.agents.intelligence.embedding_engine import EmbeddingEngine
from src.extractors.image import run_ocr
from src.common.utils import get_logger

logger = get_logger(__name__)

class ProcessingWorker:
    def __init__(self):
        self.embedder = EmbeddingEngine()
        # Uses the mapping we updated in settings.yaml
        self.extension_map = config.supported_extensions

    def _get_extractor_instance(self, ext):
        """Dynamically resolves extractor class from settings.yaml."""
        class_path = self.extension_map.get(ext)
        if not class_path:
            return None
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)()
        except Exception as e:
            logger.error(f"❌ Failed to load extractor {class_path}: {e}")
            return None

    def _is_garbage(self, text):
        """Detects if text is likely OCR noise (e.g., 'C32(.')."""
        if not text or len(text.strip()) < 15:
            return True
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        return (special_chars / len(text)) > 0.3

    def process_message(self, task: dict):
        file_path = task.get("file_path")
        ext = Path(file_path).suffix.lower()
        full_text = ""
        metadata = {}

        try:
            # 1. Dynamic Routing based on YAML
            extractor = self._get_extractor_instance(ext)
            
            if extractor:
                # FIX: Handle extractors that return (content, metadata) vs generators
                result = extractor.extract(file_path)
                
                if isinstance(result, tuple) and len(result) == 2:
                    full_text, metadata = result
                else:
                    # Fallback for list-based extractors (like Office/PDF)
                    content_items = list(result)
                    full_text = "\n".join([str(item[1]) for item in content_items if isinstance(item, (list, tuple))]).strip()
                
                # 2. High-Res Fallback for PDF/Images
                if ext in ['.pdf', '.jpg', '.png', '.jpeg'] and self._is_garbage(full_text):
                    logger.info(f"🔄 Low quality text for {ext}. Triggering high-res OCR...")
                    if hasattr(extractor, 'get_page_as_image'):
                        img = extractor.get_page_as_image(file_path)
                    else:
                        img = cv2.imread(file_path)
                    
                    if img is not None:
                        if len(img.shape) == 3 and img.shape[2] == 3:
                            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        full_text = run_ocr(img)
            
            # 3. Vectorization (Ensure we don't send empty strings to embedder)
            clean_text = full_text.strip() if full_text else f"File: {os.path.basename(file_path)}"
            vector = self.embedder.get_embeddings(clean_text[:5000])
            
            now = datetime.now().isoformat()
            
            # 4. Strict Schema Alignment for LanceDB
            return {
                "id": task.get("id"),
                "vector": vector,
                "filename": os.path.basename(file_path),
                "file_path": file_path,
                "file_type": ext.strip('.'),
                "content": clean_text,
                "tags": [],
                "source": "distributed_node",
                "engine_version": "2.3",
                "timestamp": now,
                "created_at": now,
                "category": metadata.get("category", "Unsorted"),
                "processing_status": "completed",
                "page_number": 1,
                "last_modified": os.path.getmtime(file_path),
                "issue_date": metadata.get("date", ""), 
                "expiry_date": "", 
                "primary_date": metadata.get("date", ""),
                "country": "", 
                "person": metadata.get("from", "")
            }

        except Exception as e:
            logger.error(f"❌ Critical Processing Failure for {file_path}: {str(e)}")
            return None