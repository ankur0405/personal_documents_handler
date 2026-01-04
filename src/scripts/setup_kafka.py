from confluent_kafka.admin import AdminClient, NewTopic
from src.config.loader import config
from src.common.utils import get_logger

logger = get_logger(__name__)


def setup_enterprise_topics():
    """
    Clears and creates Kafka topics for the distributed pipeline.
    - document_tasks: Input for Enrichers (6 partitions)
    - document_results: Input for the Singleton Sink (1 partition for ordering)
    """
    admin_client = AdminClient({'bootstrap.servers': config.kafka_broker})

    # Define the target state for topics
    topics_to_create = [
        # [cite_start]6 partitions allow 6 enrichers
        # to work in parallel [cite: 107]
        NewTopic("document_tasks", num_partitions=6, replication_factor=1),
        # 1 partition ensures the Sink writes documents in order
        NewTopic("document_results", num_partitions=1, replication_factor=1)
    ]

    # 1. Delete old topics to ensure a clean start
    existing_topics = admin_client.list_topics(timeout=10).topics
    topics_to_delete = [t for t in ["document_tasks", "document_results"] if t in existing_topics]

    if topics_to_delete:
        logger.info(f"🗑️ Deleting legacy topics: {topics_to_delete}")
        fs = admin_client.delete_topics(topics_to_delete)
        for topic, f in fs.items():
            try:
                f.result()
            except Exception as e:
                logger.error(f"⚠️ Deletion failed for {topic}: {e}")

    # 2. Create new topics
    logger.info("🏗️ Creating new enterprise-grade topics...")
    fs = admin_client.create_topics(topics_to_create)
    for topic, f in fs.items():
        try:
            f.result()
            logger.info(f"✅ Topic created: {topic}")
        except Exception as e:
            logger.error(f"❌ Failed to create {topic}: {e}")


if __name__ == "__main__":
    setup_enterprise_topics()
