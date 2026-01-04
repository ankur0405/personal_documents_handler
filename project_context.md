# Project Context: Personal Document Handler (PDH)

## Executive Summary
A distributed, high-performance document intelligence system designed to ingest, classify, and vectorize thousands of varied personal assets (PDFs, high-res scans, images). The system utilizes an asynchronous, event-driven architecture to manage extreme memory spikes (9GB+) inherent in OCR and ML workloads.

## Architectural Evolution
- **Current Phase**: Distributed Microservices (Migration from Local Monolith).
- **Core Strategy**: Asynchronous task orchestration via Apache Kafka to manage resource contention and backpressure.
- **Key Validation**: Successfully prototype "Three-Phase Triage" (Standard, Slices, Jumbo) to handle memory-intensive document processing.

## Technical Roadmap
1.  **Infrastructure (Active)**: Local Kafka/Zookeeper cluster deployment via Docker Compose.
2.  **Service Decoupling**: Separation of OCR/Classification (Workers) from Vectorization (Embedding Service).
3.  **State Management**: Transition from local queues to persistent Kafka offsets for fault-tolerant retries.
4.  **Advanced Features**: Implementation of semantic search, multimodal image support, and auto-categorization.

## Domain Model
- **Task**: A single unit of work (e.g., process 5 pages of a PDF).
- **Slice**: A segmented portion of a larger document to prevent RAM bloat.
- **Jumbo**: Files >150MB requiring sequential, high-resource processing

* **Documentation:**
    * **Mermaid:** Text-based diagram in `docs/architecture/system_overview.md`.
    * **Draw.io:** Visual diagram in `docs/architecture/system_overview.drawio`.

## 4. Current Folder Structure

```text
personnal_documents_handler/
├── .venv/                      # Virtual Environment
├── data/                       # Local Storage
│   ├── raw/                    # Input documents
│   └── lancedb/                # Vector Database
├── docs/                       # Project Documentation
│   └── architecture/
│       ├── system_overview.md      # Mermaid Diagram
│       └── system_overview.drawio  # Visual XML Diagram
├── src/
│   ├── main.py                 # Entry point
│   ├── agents/
│   │   ├── scanner_agent/      # File discovery
│   │   ├── classification_agent/
│   │   │   └── classifier.py   # Document classification logic
│   │   └── embedding_agent/    # CORE ENGINE
│   │       ├── embedder.py     # Orchestrator (Main Loop)
│   │       ├── worker.py       # Worker Process Logic (OCR/Chunking)
│   │       └── dashboard.py    # Tkinter UI Class (Dark Mode)
│   ├── common/
│   │   ├── db.py               # Database connection
│   │   ├── factory.py          # Extractor Factory
│   │   ├── storage.py          # File path utilities
│   │   └── utils.py
│   └── config/
│       ├── settings.yaml       # Configuration (Models, Paths)
│       └── loader.py
├── requirements.txt
└── project_context.md          # This file