import yaml
import os
from src.config.autotune import get_hardware_profile

SETTINGS_PATH = "src/config/settings.yaml"

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        raise FileNotFoundError(f"Settings file not found at {SETTINGS_PATH}")
    
    with open(SETTINGS_PATH, "r") as f:
        config = yaml.safe_load(f)

    # --- AUTO-TUNE LOGIC ---
    # Check if the user wants auto-tuning
    if config.get('system', {}).get('autotune', False):
        print("🤖 Auto-Tune Enabled: Scanning Hardware...")
        profile = get_hardware_profile()
        
        print(f"✅ Applied Profile: {profile['mode_name']}")
        
        # Override system settings with profile values
        config['system']['model_name'] = profile['model_name']
        config['system']['model_dimension'] = profile['model_dimension']
        config['system']['max_workers'] = profile['max_workers']
        # We can also inject batch_size if we move that to settings
        config['system']['batch_size'] = profile['batch_size']
        
    return config

# Load once and export
SETTINGS = load_settings()