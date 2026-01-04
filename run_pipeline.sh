#!/bin/bash

# Load 64GB Mac Environment Variables
export $(grep -v '^#' .env | xargs)

echo "🚀 Starting Kafka Infrastructure..."
docker-compose up -d zookeeper kafka

echo "⏳ Waiting for Kafka to be ready..."
sleep 10

echo "👷 Spawning $WORKER_COUNT OCR Worker Pods..."
docker-compose up -d --scale ocr-worker=$WORKER_COUNT

echo "🧠 Starting Local Embedding Service (GPU/MPS enabled)..."
# Run this in the background or a new tab to keep LanceDB access easy
python -m src.agents.embedding_agent.embedding_service &

echo "✅ System is Ready. Run 'python -m src.agents.embedding_agent.producer_service' to start ingestion."