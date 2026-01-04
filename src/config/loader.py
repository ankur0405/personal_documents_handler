import json
import yaml
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from src.common.utils import get_logger

logger = get_logger(__name__)


class AppConfig(BaseSettings):
    """
    Core Application Settings for Enterprise PDH.
    Merges settings.yaml with Environment Variables.
    """
    kafka_broker: str = Field(default="localhost:9092", validation_alias="KAFKA_BROKER")
    db_path: str = Field(default="./data/lancedb_store", validation_alias="DB_PATH")
    model_name: str = "BAAI/bge-small-en-v1.5"
    model_dimension: int = 384
    scan_root: str = Field(default="./data/smoke_test", validation_alias="SCAN_ROOT")

    # --- HARDWARE SYNC FIELDS ---
    max_workers: int = 4
    autotune: bool = True
    cleanup_temp: bool = True

    # Dictionary to hold the extension-to-extractor mapping
    supported_extensions: dict = Field(default_factory=dict)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow"  # Changed to "allow" to handle dots in YAML keys
    )

    @classmethod
    def load_config(cls):
        instance = cls()

        # Check multiple common locations for the settings file
        possible_paths = [
            Path("settings.yaml"),
            Path("config/settings.yaml"),
            Path("src/config/settings.yaml")
        ]

        yaml_path = None
        for p in possible_paths:
            if p.exists():
                yaml_path = p
                break

        if yaml_path:
            try:
                with open(yaml_path, "r") as f:
                    yaml_data = yaml.safe_load(f)
                    if yaml_data and "supported_extensions" in yaml_data:
                        instance.supported_extensions = yaml_data["supported_extensions"]

                        if "scan_root" in yaml_data:
                            instance.scan_root = yaml_data["scan_root"]

                logger.info(f"📑 Successfully loaded config from {yaml_path}")
            except Exception as e:
                logger.error(f"❌ Error parsing {yaml_path}: {e}")
        else:
            logger.error(f"❌ CRITICAL: No settings.yaml found in {possible_paths}. Current Dir: {os.getcwd()}")

        # Ensure yaml_data exists even if file load failed
        safe_yaml_data = yaml_data if yaml_path and yaml_data else {}

        if "db_path" in safe_yaml_data:
            # Convert to absolute path for cross-process consistency
            instance.db_path = str(Path(safe_yaml_data["db_path"]).absolute())
        else:
            # Fallback to a safe absolute default relative to project root
            instance.db_path = str(Path("./data/lancedb_store").absolute())

        return instance


class KnowledgeBase:

    def __init__(self, path="data/config/reference_data.json"):
        self.path = Path(path)
        self.entities = []
        self.categories = {}
        self.load()

    def load(self):
        if not self.path.exists():
            # Create directory if missing for 100-user robustness
            self.path.parent.mkdir(parents=True, exist_ok=True)
            return

        try:
            with open(self.path, "r") as f:
                data = json.load(f)
                self.entities = data.get("known_entities", [])
                self.categories = data.get("classification_rules", {})
            logger.info("🧠 Successfully synchronized Intelligence Layer.")
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")


# IMPORTANT: Call the custom loader instead of standard initialization
config = AppConfig.load_config()
knowledge = KnowledgeBase()