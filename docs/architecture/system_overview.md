# System Architecture: Distributed Ingestion Pipeline

This document outlines the enterprise-grade architecture for the **Personal Documents Handler (PDH)**. The system has evolved from a local multiprocessing monolith to a decoupled, event-driven microservice architecture using **Apache Kafka** to manage hardware resource contention on Apple Silicon.

---

## 1. High-Level Architecture Flow
The following diagram illustrates the data lifecycle from initial discovery on the file system through the Kafka message backbone to final persistence in LanceDB.

```mermaid
graph LR
    subgraph Ingestion
        A[File System] --> B[Producer Service]
    end

    subgraph Messaging_Backbone
        B -->|raw_tasks| K1((Kafka))
        K1 --> C[Orchestrator]
        C -->|page_slices| K2((Kafka))
    end

    subgraph Worker_Cluster
        K2 --> D1[Worker Pod 1]
        K2 --> D2[Worker Pod 2]
        K2 --> DN[Worker Pod N]
    end

    subgraph Persistence
        D1 & D2 & DN -->|processed_text| K3((Kafka))
        K3 --> E[Embedding Service]
        E --> F[(LanceDB)]
    end

    style K1 fill:#fff2cc,stroke:#d6b656
    style K2 fill:#fff2cc,stroke:#d6b656
    style K3 fill:#fff2cc,stroke:#d6b656
    style F fill:#dae8fc,stroke:#6c8ebf

sequenceDiagram
    autonumber
    participant FS as External Drive
    participant P as Ingestion Service (Producer)
    participant K1 as Kafka: raw_tasks
    participant O as Orchestrator (Slicer)
    participant K2 as Kafka: process_queue
    participant W as OCR Worker Cluster (Consumer)
    participant K3 as Kafka: processed_content
    participant E as Embedding Service
    participant DB as LanceDB (Vector Store)

    Note over P,O: Phase 1: Ingestion & Slicing
    FS->>P: Discovery (Scan Files)
    P->>P: Triage (Size Check > 150MB)
    P->>K1: Publish File Metadata
    K1-->>O: Consume Task
    O->>O: Slicing (10+ pages -> 5-page slices)
    O->>K2: Publish Slices

    Note over W,DB: Phase 2: Processing & Persistence
    K2-->>W: Consume Slice (Pull-based)
    W->>W: PaddleOCR / Classification
    W->>K3: Publish Extracted Text + Metadata
    K3-->>E: Consume Results
    E->>E: Vectorization (Sentence-Transformers)
    E->>DB: table.add(chunk_data, mode="append")
```