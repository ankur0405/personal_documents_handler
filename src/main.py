import os
import json
import lancedb
from pathlib import Path
from kafka import KafkaAdminClient, KafkaProducer
from kafka.admin import NewTopic
from src.config.loader import config
from src.common.utils import get_logger

logger = get_logger(__name__)


class DiscoveryProducer:

    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=config.kafka_broker,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all'
        )
        self.db_path = "data/lancedb_store"
        self._ensure_topic_exists()

    def _ensure_topic_exists(self):
        """Ensures the Kafka topic is ready for 100-user throughput."""
        try:
            admin = KafkaAdminClient(bootstrap_servers=config.kafka_broker)
            topic_name = 'document_tasks'
            if topic_name not in admin.list_topics():
                topic = NewTopic(name=topic_name, num_partitions=3, replication_factor=1)
                admin.create_topics([topic])
                logger.info(f"🆕 Created Kafka topic: {topic_name}")
            admin.close()
        except Exception as e:
            logger.warning(f"⚠️ Topic check skipped: {e}")

    def get_indexed_files(self):
        """Fetches list of already processed files to prevent duplicates."""
        try:
            if not os.path.exists(self.db_path):
                return set()
            db = lancedb.connect(self.db_path)
            if "document_intel" not in db.list_tables():
                return set()
            table = db.open_table("document_intel")
            # Pull only file paths to minimize memory usage
            df = table.to_pandas()
            return set(df['file_path'].tolist()) if not df.empty else set()
        except Exception as e:
            logger.error(f"❌ DB Reconciliation failed: {e}")
            return set()

    def discover_and_publish(self):
        logger.info("🚀 PDH Enterprise Pipeline Initializing...")

        indexed_files = self.get_indexed_files()
        logger.info(f"--- 🧹 RECONCILIATION: {len(indexed_files)} files already in DB ---")

        scan_dir = Path(config.scan_root)
        logger.info(f"🔎 Scanning Directory: {scan_dir.absolute()}")

        # We keep the dots because your YAML has them: {'.docx', '.pdf', '.eml', ...}
        valid_exts = {ext.lower() for ext in config.supported_extensions.keys()}

        new_tasks_count = 0

        for file_path in scan_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # pathlib.suffix returns the dot (e.g., '.eml')
            ext = file_path.suffix.lower() 
            str_path = str(file_path.absolute())

            # Check against your YAML keys (which also have dots)
            if ext in valid_exts and str_path not in indexed_files:
                task = {
                    "id": f"task_{int(os.path.getmtime(str_path))}_{new_tasks_count}",
                    "file_path": str_path,
                    "filename": file_path.name,
                    "priority": "normal",
                    "timestamp": os.path.getmtime(str_path)
                }

                self.producer.send('document_tasks', task)
                logger.info(f"📤 Published to Kafka: {file_path.name}")
                new_tasks_count += 1
            elif ext not in valid_exts:
                # This will help us see if any strange extensions are skipping
                logger.debug(f"⏩ Ignoring unsupported file type: {file_path.name} ({ext})")

        self.producer.flush()
        logger.info(f"✅ Discovery Sync Complete. Published {new_tasks_count} new tasks.")


if __name__ == "__main__":
    producer = DiscoveryProducer()
    producer.discover_and_publish()