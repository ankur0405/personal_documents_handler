import fitz  # PyMuPDF
import numpy as np
from pathlib import Path
from src.common.utils import get_logger

logger = get_logger(__name__)

class PDFExtractor:
    def __init__(self):
        pass

    def extract(self, file_path):
        """
        Yields (page_num, text) for the digital layer of the PDF.
        """
        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                yield page_num + 1, text
            doc.close()
        except Exception as e:
            logger.error(f"❌ Digital PDF extraction failed for {file_path}: {e}")

    def get_page_as_image(self, file_path, page_num=0, dpi=300):
        """
        Converts a specific PDF page to a high-res numpy array for OCR.
        Required when the digital layer is garbled or missing.
        """
        doc = fitz.open(file_path)
        page = doc.load_page(page_num)
        
        # Scaling matrix for 300 DPI (72 is default PDF resolution)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        
        # Convert pixmap to numpy array (H, W, C)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
        doc.close()
        return img