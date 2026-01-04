FROM python:3.12-slim

# Add unarchiving utilities (unzip, tar, unrar-free)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    gcc \
    python3-dev \
    unzip \
    tar \
    unrar-free \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt patool # Added patool here
RUN pip install --no-cache-dir confluent-kafka
COPY src/ ./src/
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "src.agents.embedding_agent.producer_service"]