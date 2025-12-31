import json
import os
from typing import Tuple, List

def load_category_config() -> Tuple[str, List[str]]:
    """
    Reads the category list from src/config/reference_data.json.
    
    Returns:
        prompt_string (str): A formatted string ready to be injected into an LLM prompt.
        valid_ids (List[str]): A list of valid IDs for validation logic.
    """
    # 1. Determine the path dynamically based on this file's location
    # This file is in: src/utils/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up one level to 'src/'
    src_dir = os.path.dirname(current_dir)
    
    # Go down into 'config/' to find the json
    config_path = os.path.join(src_dir, "config", "reference_data.json")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file missing at: {config_path}")
        
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing reference_data.json: {e}")
    
    categories = data.get("document_categories", [])
    
    prompt_lines = []
    valid_ids = []
    
    for cat in categories:
        # We include the description to help the AI understand nuances
        line = f"- {cat['display_name']} (ID: '{cat['id']}'): {cat['description']}"
        prompt_lines.append(line)
        valid_ids.append(cat['id'])
        
    return "\n".join(prompt_lines), valid_ids

if __name__ == "__main__":
    # Test block to verify paths
    try:
        prompt, ids = load_category_config()
        print(f"✅ Configuration loaded successfully.")
        print(f"Found {len(ids)} categories.")
    except Exception as e:
        print(f"❌ Error: {e}")