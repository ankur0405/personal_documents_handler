import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from src.common.utils import get_logger

logger = get_logger(__name__)

class AppConfig(BaseSettings):
    """
    Core Application Settings.
    Prioritizes Environment Variables over the YAML file.
    """
    kafka_broker: str = Field(default="localhost:9092", validation_alias="KAFKA_BROKER")
    db_path: str = Field(default="./data/lancedb_store", validation_alias="DB_PATH")
    model_name: str = "BAAI/bge-small-en-v1.5"
    model_dimension: int = 384
    scan_root: str = Field(default="./storage", validation_alias="SCAN_ROOT")
    
    # --- HARDWARE SYNC FIELDS ---
    max_workers: int = 4  
    autotune: bool = True
    cleanup_temp: bool = True
    # Populate extensions as a dictionary to match settings.yaml
    supported_extensions: dict = {}

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

class KnowledgeBase:
    def __init__(self, path="data/config/reference_data.json"):
        self.path = Path(path)
        self.entities = []
        self.categories = {}
        self.load()

    def load(self):
        if not self.path.exists(): return
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
                self.entities = data.get("known_entities", [])
                self.categories = data.get("classification_rules", {})
            logger.info("Successfully synchronized Intelligence Layer.")
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")

config = AppConfig()
knowledge = KnowledgeBase()