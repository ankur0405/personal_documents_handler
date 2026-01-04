# File: docker/worker.Dockerfile
FROM python:3.12-slim

# Install modern system dependencies for PaddleOCR and OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libnss3 \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir confluent-kafka

# Copy source code
COPY src/ ./src/

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "src.agents.embedding_agent.worker_service"]