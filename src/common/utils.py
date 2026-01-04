import logging
import os
from pathlib import Path


def get_logger(name: str):
    """
    Enterprise logger that routes all output to the centralized
    data/logs directory. Fixed to avoid circular imports.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Determine log directory without importing config
        # Fallback to local 'data/logs' if no environment variable is set
        db_path = os.environ.get("DB_PATH", "./data/lancedb_store")
        log_dir = Path(db_path).parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        file_handler = logging.FileHandler(log_dir / "system.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
