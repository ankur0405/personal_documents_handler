import fitz  # PyMuPDF
import cv2
import numpy as np
from .base import BaseExtractor
from .image import run_ocr  # Import the shared OCR tool

class PDFExtractor(BaseExtractor):
    def extract(self, file_path):
        try:
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                # 1. Try Standard Extraction
                text = page.get_text()
                
                # 2. Gibberish Detection
                is_gibberish = False
                if len(text) > 50 and (text.count(' ') / len(text)) < 0.05:
                    is_gibberish = True
                if "flfi" in text or "fifl" in text:
                    is_gibberish = True
                    
                if is_gibberish:
                    text = "" # Discard to force OCR
                
                # 3. Fallback to OCR
                if not text.strip():
                    try:
                        pix = page.get_pixmap(dpi=300)
                        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                        if pix.n == 4:
                            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
                        
                        text = run_ocr(img_array)
                    except Exception as e:
                        print(f"⚠️ OCR Failed for PDF page {i}: {e}")

                if text.strip():
                    yield i + 1, text
                    
        except Exception as e:
            print(f"⚠️ PDF Error {file_path}: {e}")