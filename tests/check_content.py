import sys
import os
import pandas as pd

# Path Setup
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.common.db import get_table

def check_extraction_status():
    print("--- 🕵️‍♂️ Content Extraction Report ---")
    
    table = get_table()
    df = table.to_pandas()
    
    # Filter for interesting types
    images = df[df['file_type'].isin(['jpg', 'png', 'jpeg', 'heic'])]
    slides = df[df['file_type'].isin(['pptx', 'ppt'])]
    
    print(f"📊 Total Documents: {len(df)}")
    print(f"🖼️  Images Found: {len(images)}")
    print(f"aa  Slides Found: {len(slides)}")
    
    print("\n--- 📸 Image OCR Samples (First 3) ---")
    if images.empty:
        print("❌ No images indexed.")
    else:
        for i, row in images.head(3).iterrows():
            preview = row['content'][:100].replace('\n', ' ')
            status = "✅ TEXT FOUND" if len(preview) > 10 else "⚠️  NO TEXT (Maybe blurry?)"
            print(f"[{status}] {row['filename']} -> \"{preview}...\"")

    print("\n--- 📽️  PowerPoint Samples (First 3) ---")
    if slides.empty:
        print("❌ No slides indexed.")
    else:
        for i, row in slides.head(3).iterrows():
            preview = row['content'][:100].replace('\n', ' ')
            status = "✅ TEXT FOUND" if len(preview) > 10 else "⚠️  NO TEXT"
            print(f"[{status}] {row['filename']} -> \"{preview}...\"")

if __name__ == "__main__":
    check_extraction_status()