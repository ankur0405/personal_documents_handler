import psutil
import torch
import logging
import os
from src.config.loader import config  # Centralized path & settings resolver

logger = logging.getLogger(__name__)


def get_hardware_profile():
    """
    Dynamically calculates optimal worker counts and hardware acceleration
    using the centralized AppConfig class.
    """
    # 1. Access settings via the validated config object
    autotune_enabled = config.autotune

    # 2. Detect System Resources
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    cpu_count = psutil.cpu_count(logical=False) or 2

    # 3. Calculate "Safe" Workers (50% Utilization Cap
    # for system responsiveness)
    if ram_gb >= 16:
        calculated_workers = max(2, int(cpu_count // 3))
    else:
        calculated_workers = 2

    # 4. Check for GPU/Accelerator (MPS for your Mac)
    has_gpu = torch.cuda.is_available() or (
        hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
    )

    # 5. Determine Hardware Profile Key
    if ram_gb >= 32 and (cpu_count >= 8 or has_gpu):
        mode_name = "High Performance"
        device = "mps" if has_gpu else "cpu"
    elif ram_gb >= 12:
        mode_name = "Balanced"
        device = "cpu"
    else:
        mode_name = "Entry Level"
        device = "cpu"

    # 6. Build Final Validated Profile
    final_profile = {
        "mode_name": mode_name,
        "model_name": config.model_name,
        "model_dimension": config.model_dimension,
        "device": device,
        "max_workers": calculated_workers if autotune_enabled else getattr(config, 'max_workers', 4)
    }

    # Environment override check (Highest priority)
    env_max_workers = os.environ.get('MAX_WORKERS')
    if env_max_workers:
        final_profile['max_workers'] = int(env_max_workers)

    print(f"✅ Auto-Tune: {final_profile['mode_name']} | "
        f"Workers: {final_profile['max_workers']} | Device: {final_profile['device']}")

    return final_profile
