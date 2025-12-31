import psutil
import torch
import logging
import os
import yaml

logger = logging.getLogger(__name__)

def load_raw_settings():
    """
    Safely loads settings.yaml. Returns empty dict if file fails.
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "settings.yaml")
        if not os.path.exists(config_path):
            print(f"⚠️ Warning: Settings file not found at {config_path}. Using defaults.")
            return {}
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"⚠️ Warning: Failed to load settings.yaml: {e}")
        return {}

def get_hardware_profile():
    """
    Analyzes hardware and returns a config dictionary.
    Guarantees keys exists to prevent Loader crashes.
    """
    # 1. Load the "Source of Truth" from YAML
    raw_config = load_raw_settings()
    system_defaults = raw_config.get('system', {})
    profiles_config = raw_config.get('hardware_profiles', {})

    # 2. Detect Resources
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    cpu_count = psutil.cpu_count(logical=False) or 2
    
    has_cuda = torch.cuda.is_available()
    has_mps = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
    gpu_available = has_cuda or has_mps
    
    print(f"🤖 Auto-Tune: Detected {ram_gb:.1f}GB RAM, {cpu_count} Cores, GPU={'Yes' if gpu_available else 'No'}")

    # 3. Select the Base Profile Key
    if ram_gb >= 32 and (cpu_count >= 8 or gpu_available):
        selected_key = "high_performance"
    elif ram_gb >= 12:
        selected_key = "balanced"
    else:
        selected_key = "entry_level"

    # 4. Construct the Final Profile with FALLBACKS
    # We intentionally default to BAAI/Small to prevent crashes if YAML is empty
    final_profile = {
        "model_name": "BAAI/bge-small-en-v1.5",
        "model_dimension": 384,
        "chunk_size": 1000,
        "chunk_overlap": 100
    }
    
    # Override with YAML system defaults if they exist
    final_profile.update(system_defaults)
    
    # Get the hardware specific overrides from YAML
    hardware_override = profiles_config.get(selected_key, {})
    final_profile.update(hardware_override)

    # 5. Dynamic Calculation (Force these values to exist)
    if selected_key == "entry_level":
        final_profile['mode_name'] = final_profile.get('mode_name', "Entry Level")
        final_profile['batch_size'] = final_profile.get('batch_size', 16)
        final_profile['max_workers'] = 2
        final_profile['device'] = "cpu"
        
    elif selected_key == "balanced":
        final_profile['mode_name'] = final_profile.get('mode_name', "Balanced Mode")
        final_profile['batch_size'] = final_profile.get('batch_size', 32)
        final_profile['max_workers'] = max(2, cpu_count // 2)
        final_profile['device'] = "mps" if has_mps else ("cuda" if has_cuda else "cpu")
        
    elif selected_key == "high_performance":
        final_profile['mode_name'] = final_profile.get('mode_name', "High Performance")
        final_profile['batch_size'] = final_profile.get('batch_size', 64)
        final_profile['max_workers'] = max(4, cpu_count - 2)
        final_profile['device'] = "mps" if has_mps else ("cuda" if has_cuda else "cpu")

    print(f"✅ Auto-Tune Selected: {final_profile['mode_name']}")
    
    return final_profile