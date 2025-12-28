import cv2
import numpy as np
import warnings
import logging
import os

# 1. AGGRESSIVE SILENCING
# Silence standard warnings
warnings.filterwarnings("ignore")

# Silence Paddle's internal loggers
logging.getLogger("ppocr").setLevel(logging.CRITICAL)
logging.getLogger("paddlex").setLevel(logging.CRITICAL) # <--- This stops the "Creating model" spam

# Redirect system stdout/stderr to devnull during import if needed (Advanced silence)
# usually the logging lines above are enough.

from paddleocr import PaddleOCR
from .base import BaseExtractor

# --- SINGLETON INSTANCE ---
# We enable 'use_angle_cls=True' here.
# The logger fixes above should keep this quiet now.
ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')

def resize_if_huge(image):
    """
    If an image is massive (>2500px), resize it down.
    OCR doesn't need 12k resolution; 2.5k is plenty.
    """
    MAX_DIM = 2500
    h, w = image.shape[:2]
    
    if max(h, w) > MAX_DIM:
        scale = MAX_DIM / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return image

def run_ocr(image_array):
    try:
        # 1. SAFETY: Downscale huge images
        safe_image = resize_if_huge(image_array)
        
        # 2. Run OCR
        # We removed 'cls=True' to fix the version bug.
        result = ocr_engine.ocr(safe_image)
        
        if not result or result[0] is None:
            return ""
            
        text_lines = [line[1][0] for line in result[0]]
        return " ".join(text_lines)
        
    except Exception as e:
        # Only print actual errors, not warnings
        print(f"⚠️ PaddleOCR Error: {e}")
        return ""

class ImageExtractor(BaseExtractor):
    def extract(self, file_path):
        try:
            image = cv2.imread(file_path)
            if image is None: return

            text = run_ocr(image)
            if text.strip():
                yield 1, text
        except Exception as e:
            print(f"⚠️ Image Error {file_path}: {e}")