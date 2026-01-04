#!/bin/bash

# --- CONFIGURATION ---
PROJECT_NAME="personnal_documents_handler"
DEPLOY_CONFIG="deploy/docker-compose.yml"
ENV_FILE=".env"

echo "🧹 [1/5] Cleaning up legacy and phantom resources..."

# 1. Kill old project containers if they exist
docker compose -p $PROJECT_NAME down --remove-orphans 2>/dev/null

# 2. Check for port 9092 conflict (Ghost Kafka)
GHOST_PID=$(lsof -t -i:9092)
if [ ! -z "$GHOST_PID" ]; then
    echo "⚠️  Found ghost process on port 9092 (PID: $GHOST_PID). Terminating..."
    kill -9 $GHOST_PID
fi

# 3. Terminate any lingering local Python service nodes
echo "Stopping any existing local service nodes..."
pkill -f "src.services.sink_node"
pkill -f "src.services.enricher_node"

echo "🚀 [2/5] Starting Infrastructure (Kafka/Zookeeper)..."
# Start the new infrastructure defined in the deploy folder
docker-compose --env-file $ENV_FILE -f $DEPLOY_CONFIG up -d

echo "⏳ [3/5] Waiting for Kafka broker to stabilize (10s)..."
sleep 10

echo "🏗️  [4/5] Initializing Enterprise Kafka Topics..."
# Execute the refactored setup script to create partitioned topics
python3 -m src.scripts.setup_kafka

echo "🧠 [5/5] Launching Distributed Service Tier..."

# Start the Singleton Sink (The Writer) in the background
python3 -m src.services.sink_node > data/logs/sink.log 2>&1 &
echo "✅ Sink Node started (Logging to data/logs/sink.log)"

# Start the Enricher (The AI Muscle) in the background
python3 -m src.services.enricher_node > data/logs/enricher.log 2>&1 &
echo "✅ Enricher Node started (Logging to data/logs/enricher.log)"

echo "--------------------------------------------------------"
echo "🌟 SYSTEM READY: Starting Discovery Producer (Main)"
echo "--------------------------------------------------------"

# Run the Producer in the foreground to monitor progress
python3 src/main.py

echo "🏁 Pipeline run finished. Services are still running in background."
echo "Use 'pkill -f src.services' to stop background nodes."