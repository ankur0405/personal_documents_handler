import psutil
import os
import platform

def get_hardware_profile():
    """
    Returns system capacity for Dynamic Scaling.
    """
    try:
        # Get Physical Cores (This is our Theoretical Max Speed)
        cpu_cores = psutil.cpu_count(logical=False) or 4
        # Logical cores for hyperthreading systems
        logical_cores = psutil.cpu_count(logical=True) or 4
        
        vm = psutil.virtual_memory()
        total_ram_gb = vm.total / (1024 ** 3)
    except:
        cpu_cores = 4
        logical_cores = 8
        total_ram_gb = 16.0

    print(f"🖥️  Hardware Detected: {total_ram_gb:.1f}GB RAM | {cpu_cores} Phys Cores | {logical_cores} Threads")

    # We allow the pool to be as large as the logical core count.
    # The 'Smart Feeder' will ensure we don't use them all if RAM is tight.
    max_potential_workers = max(2, logical_cores) 

    # Profile Config
    return {
        "mode_name": "🚀 Dynamic Adaptive Mode",
        "model_name": "BAAI/bge-large-en-v1.5", 
        "model_dimension": 1024,
        # We set the POOL size high, but we throttle utilization dynamically
        "max_workers": max_potential_workers,
        "chunk_size": 1000
    }