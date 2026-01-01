import os
import yaml
import logging

# Set up logging
logger = logging.getLogger(__name__)

def load_settings():
    """
    Loads settings.yaml and applies hardware auto-tuning overrides.
    """
    # 1. Find the settings file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "settings.yaml")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"❌ Critical: Settings file missing at {config_path}")

    # 2. Load the YAML
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    # Ensure critical sections exist
    if 'system' not in config: config['system'] = {}
    if 'performance' not in config: config['performance'] = {}

    # 3. Apply Auto-Tune (if enabled)
    # We do this inside a try-block so a tuning error doesn't kill the app
    try:
        from src.config.autotune import get_hardware_profile
        
        # Only run autotune if it's enabled in YAML
        if config['system'].get('autotune', True):
            profile = get_hardware_profile()
            
            # DYNAMIC MERGE: Update system config with profile values
            # This prevents KeyError because we don't hardcode keys like 'batch_size'
            config['system'].update(profile)
            
            # Special handling: If profile has 'max_workers', ensure it overrides system
            if 'max_workers' in profile:
                config['system']['max_workers'] = profile['max_workers']

    except ImportError:
        logger.warning("⚠️ Auto-tune module not found. Using default settings.")
    except Exception as e:
        logger.warning(f"⚠️ Auto-tune failed: {e}. Using default settings.")

    # 4. Defaults for Safety (If YAML is missing keys)
    # These ensure the code never crashes even if you delete lines in YAML
    defaults = {
        'chunk_size': 1000,
        'chunk_overlap': 100,
        'model_name': "BAAI/bge-small-en-v1.5",
        'model_dimension': 384,
        'max_workers': 2
    }
    
    for key, val in defaults.items():
        if key not in config['system']:
            config['system'][key] = val

    return config

# Load once and export
SETTINGS = load_settings()