import sys
import os
import numpy as np

# Path Setup
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.common.db import get_table

def check_vectors():
    table = get_table()
    # Get the first item
    df = table.head(1).to_pandas()
    
    if df.empty:
        print("❌ Database is empty.")
        return

    # Check the vector column
    vector = df.iloc[0]['vector']
    
    print(f"📄 File: {df.iloc[0]['filename']}")
    print(f"📏 Vector Length: {len(vector)}")
    print(f"🧮 Vector Sample: {vector[:5]}") # Print first 5 numbers
    
    # Check if all are zero
    if np.allclose(vector, 0):
        print("\n❌ DIAGNOSIS: Vector is all Zeros. The Embedding save failed.")
    else:
        print("\n✅ DIAGNOSIS: Vector contains data.")

if __name__ == "__main__":
    check_vectors()