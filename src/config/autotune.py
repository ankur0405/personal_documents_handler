import psutil
import torch
import logging
import os
import yaml

logger = logging.getLogger(__name__)

def load_raw_settings():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "settings.yaml")
        if not os.path.exists(config_path): return {}
        with open(config_path, 'r') as f: return yaml.safe_load(f) or {}
    except: return {}

def get_hardware_profile():
    # 1. Load Defaults
    raw_config = load_raw_settings()
    system_defaults = raw_config.get('system', {})
    profiles_config = raw_config.get('hardware_profiles', {})

    # 2. Detect Resources
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    cpu_count = psutil.cpu_count(logical=False) or 2
    
    # 3. Calculate "Safe" Workers based on Hardware
    #    Rule: Use exactly 50% of cores to ensure system responsiveness
    if ram_gb >= 16:
        # User Requested: 50% Utilization Cap
        calculated_workers = max(2, int(cpu_count // 3))
    else:
        # Low Spec: Keep it minimal
        calculated_workers = 2

    # 4. Environment Overrides (Highest Priority)
    env_max_workers = os.environ.get('MAX_WORKERS')
    
    # 5. Determine Profile Key
    has_gpu = torch.cuda.is_available() or (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available())
    if ram_gb >= 32 and (cpu_count >= 8 or has_gpu):
        selected_key = "high_performance"
    elif ram_gb >= 12:
        selected_key = "balanced"
    else:
        selected_key = "entry_level"

    # 6. Build Final Config
    final_profile = {
        "model_name": "BAAI/bge-small-en-v1.5",
        "model_dimension": 384,
        "device": "mps" if has_gpu else "cpu"
    }
    
    # Apply YAML defaults
    final_profile.update(system_defaults)
    
    # --- THE FIX: FORCE 50% CALCULATION ---
    # If Autotune is ON, we overwrite the YAML default with our 50% calculation
    if system_defaults.get('autotune', True) and not env_max_workers:
        final_profile['max_workers'] = calculated_workers

    # Apply Hardware Profile overrides (if any exist in YAML)
    final_profile.update(profiles_config.get(selected_key, {}))

    # Final env var override check
    if env_max_workers:
        final_profile['max_workers'] = int(env_max_workers)

    print(f"✅ Auto-Tune: {final_profile.get('mode_name', selected_key)} | Workers: {final_profile['max_workers']} | Device: {final_profile['device']}")
    
    return final_profile