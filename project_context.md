# Project Context: Personal Documents Handler (Local RAG)

## 1. Project Overview
A high-performance, local-first RAG (Retrieval Augmented Generation) pipeline designed to ingest, classify, and index personal documents (PDFs, Images) into a LanceDB vector database. The system is optimized for macOS (Apple Silicon) and prioritizes stability over raw speed, using a "Supervisor" architecture to manage memory leaks and system resource usage.

## 2. Current Architecture: "The Decoupled Supervisor"
We have implemented a **3-Tier Decoupled Architecture** to ensure the UI remains responsive while heavy AI tasks run in the background.

### **The Three Tiers**
1.  **The Orchestrator (`embedder.py`):**
    * **Role:** The "Boss" / Middleman.
    * **Responsibilities:** Manages the process pool, polls the `ResultQueue`, updates the UI, and writes to LanceDB.
    * **Logic:** Uses a "Sniper" to kill workers using >4GB RAM and an "Auto-Scaler" to spawn new workers if CPU < 50%.
2.  **The Worker (`worker.py`):**
    * **Role:** The "Labor."
    * **Responsibilities:** Performs OCR, Classification, and Chunking in a separate memory space.
    * **Communication:** Throttles UI updates (max 1 msg every 0.3s) to prevent queue flooding.
3.  **The Dashboard (`dashboard.py`):**
    * **Role:** The "Face."
    * **Style:** Modern "Dark Mode" theme (`#2b2b2b` background) with card-based worker rows.
    * **Function:** Pure visualization. It receives updates from the Orchestrator, never directly from workers.

## 3. Key Technical Decisions
* **Throttled IPC:** Workers buffer their progress and only ping the main process 3 times per second to prevent "event storms."
* **Visual Feedback:**
    * **Global Bar:** Shows overall files processed + ETA.
    * **Worker Cards:** Show distinct status (Filename + Progress Bar) for each process.
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