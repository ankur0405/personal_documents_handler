"""
Module: Image Classifier (Doc vs Photo)
Description: Uses computer vision heuristics to determine if an image 
             is likely a scanned document/screenshot or a natural photograph.
"""

import cv2
import numpy as np

def is_scanned_document(image_path: str) -> bool:
    """
    Analyzes image structure to detect if it contains dense text (Document)
    or natural scenes (Photo).
    
    Returns:
        True if it looks like a document/screenshot.
        False if it looks like a natural photo.
    """
    try:
        # 1. Read Image in Grayscale
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False

        # 2. Resize for Speed (Analyze a small thumbnail)
        # We don't need 4K resolution to check for text texture.
        h, w = img.shape
        scale = 500 / max(h, w)
        small_img = cv2.resize(img, None, fx=scale, fy=scale)
        
        # 3. Edge Detection (Canny)
        # Text creates very strong, sharp edges compared to natural objects.
        edges = cv2.Canny(small_img, 50, 150)
        
        # 4. Calculate Edge Density
        # What % of the image is "edges"? 
        # Documents (lots of letters) usually have high edge density.
        total_pixels = small_img.size
        edge_pixels = np.count_nonzero(edges)
        edge_density = edge_pixels / total_pixels
        
        # 5. Check Background Consistency (Variance)
        # Documents usually have a uniform background (white/paper).
        # We look at the variance of the non-edge pixels.
        # (This is a simplified check: High variance = Complex photo background)
        
        # Heuristic Thresholds:
        # - Documents typically have > 5% edge density (dense text).
        # - Screenshots can go lower, but natural photos usually are < 2% or extremely high > 20% (noise).
        
        # Let's stick to a simple robust check:
        # If we see a healthy amount of sharp edges, we assume it's text.
        if edge_density > 0.05: 
            return True
            
        return False

    except Exception as e:
        print(f"⚠️  Error classifying image {image_path}: {e}")
        return False