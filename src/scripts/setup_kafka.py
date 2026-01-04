from confluent_kafka.admin import AdminClient, NewTopic
import os
from dotenv import load_dotenv

load_dotenv()

def create_pdh_topics():
    # Use the LOCAL address (localhost:9092)
    admin_client = AdminClient({
        'bootstrap.servers': os.getenv('KAFKA_BROKER_LOCAL', 'localhost:9092')
    })

    # Define topics with 6 partitions to match your 6 workers
    topic_list = [
        NewTopic("standard_tasks", num_partitions=6, replication_factor=1),
        NewTopic("paginated_tasks", num_partitions=6, replication_factor=1),
        NewTopic("jumbo_tasks", num_partitions=1, replication_factor=1), # Sequential only
        NewTopic("processed_content", num_partitions=6, replication_factor=1)
    ]

    # Create topics
    fs = admin_client.create_topics(topic_list)

    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            print(f"Topic '{topic}' created successfully.")
        except Exception as e:
            print(f"Failed to create topic '{topic}': {e}")

if __name__ == "__main__":
    create_pdh_topics()