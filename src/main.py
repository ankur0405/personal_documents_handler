import sys
import os
from src.agents.scanner_agent.scanner import scan_directory

# --- PATH SETUP ---
# We need to add the project root to Python's system path.
# This ensures that when we run this script, it can see the 'src' package.
# 'os.path.dirname(__file__)' is the src/ folder.
# '..' goes up one level to 'personnal_documents_handler/'.
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# --- CONFIGURATION ---
# Define the target folder to scan.
# For Production, this will eventually come from a UI selector.
# For now, we point to our local test data or external drive.
TARGET_FOLDER = "/volumes/Extreme SSD/Documents"
# Example External Drive: "/Volumes/Samsung T7/MyArchives"

if __name__ == "__main__":
    """
    Main Execution Block.
    This checks if the script is being run directly (not imported).
    """
    try:
        print("--- 🚀 Starting Document Scanner Agent ---")
        scan_directory(TARGET_FOLDER)
        print("--- 🏁 Agent Task Finished Successfully ---")

    except Exception as e:
        print(f"❌ Critical Application Error: {e}")