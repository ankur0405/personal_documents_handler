import fitz  # PyMuPDF
import cv2
import numpy as np
from .base import BaseExtractor
from .image import run_ocr

class PDFExtractor(BaseExtractor):
    def extract(self, file_path, page_range=None):
        """
        Extracts text from a PDF, falling back to OCR if needed.
        Supports specific page ranges for parallel processing.
        """
        try:
            doc = fitz.open(file_path)
            
            # Determine which pages to process
            if page_range:
                start, end = page_range
                pages_to_scan = range(start, min(end, len(doc)))
            else:
                pages_to_scan = range(len(doc))

            for i in pages_to_scan:
                page = doc[i]
                text = page.get_text()
                
                # Gibberish Detection
                is_gibberish = False
                if len(text) > 50 and (text.count(' ') / len(text)) < 0.05:
                    is_gibberish = True
                
                if is_gibberish or not text.strip():
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