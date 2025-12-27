import sys
import os
import warnings # <--- Add this

# --- SILENCE MPS WARNINGS ---
# Apple Silicon (MPS) doesn't support 'pin_memory' yet, but libraries request it anyway.
# We filter this specific warning to keep the logs clean.
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", category=UserWarning, module='torch.utils.data.dataloader')

# --- PATH SETUP ---
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.agents.scanner_agent.scanner import scan_directory
from src.agents.embedding_agent.embedder import embed_documents

# --- CONFIGURATION ---
TARGET_FOLDER = "/volumes/Extreme SSD/Documents"

if __name__ == "__main__":
    try:
        print("--- 🏁 STARTING PIPELINE ---")
        
        # Step 1: Scan for new/modified files
        print("\n--- [STEP 1] SCANNING ---")
        scan_directory(TARGET_FOLDER)
        
        # Step 2: Generate AI Embeddings
        print("\n--- [STEP 2] EMBEDDING ---")
        embed_documents()
        
        print("\n--- 🎉 PIPELINE FINISHED SUCCESSFULLY ---")
        
    except KeyboardInterrupt:
        print("\n🛑 Pipeline stopped by user.")
    except Exception as e:
        print(f"\n❌ Critical Error: {e}")