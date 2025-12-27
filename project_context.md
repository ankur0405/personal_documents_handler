# 📂 Personal Document Intelligence Agent

**Current Status:** Phase 6 (The "Cockpit" - Streamlit UI & Self-Healing Database)  
**Last Updated:** December 2025  
**Description:** A local, privacy-first AI search engine for personal files. It indexes Documents, Images, Emails, and Slides using vector embeddings and OCR, enabling semantic search via a web dashboard.

---

## 🏗 System Architecture

### **Core Design Patterns**
* **Factory Pattern:** Dynamically loads file handlers (`PDFExtractor`, `ImageExtractor`) based on `settings.yaml`.
* **Parallel Incremental Engine:**
    * **Delta Loading:** Only processes new or modified files (checks timestamps + vectors).
    * **Self-Healing:** Automatically detects and removes duplicate "Skeleton" records.
    * **Concurrency:** Uses `ProcessPoolExecutor` (10 workers) for high-speed indexing on Apple Silicon.
* **Vector Search:** Uses `LanceDB` for serverless storage and `all-MiniLM-L6-v2` for semantic retrieval.
* **User Interface:** A Streamlit web dashboard for visual search and preview.

### **Tech Stack**
* **Language:** Python 3.12+
* **Frontend:** Streamlit
* **Database:** LanceDB
* **AI Model:** `sentence-transformers/all-MiniLM-L6-v2`
* **OCR/Vision:** `EasyOCR` + `OpenCV`
* **File Parsing:** `PyMuPDF`, `python-docx`, `python-pptx`, `extract-msg`, `pandas`

---

## 📂 Directory Structure

```text
src/
├── agents/
│   ├── embedding_agent/      # The "Brain" (Parallel Incremental Engine)
│   │   └── embedder.py       # Handles Delta Loading & Deduplication
│   └── search_agent/         # The Retrieval Logic
│       └── search.py         # Returns structured results (List of Dicts)
├── common/
│   ├── db.py                 # LanceDB Schema & Connection
│   ├── interfaces.py         # BaseExtractor (Abstract Base Class)
│   ├── factory.py            # ExtractorFactory (Plugin Manager)
│   ├── extractors.py         # Concrete Classes (PDF, Doc, OCR, etc.)
│   └── image_classifier.py   # Vision Heuristic (Doc vs Photo)
├── config/
│   ├── loader.py             # YAML Loader Singleton
│   └── settings.yaml         # Central Control (Extensions, Workers)
├── utils/
│   └── clean_db.py           # Aggressive Deduplication Tool
├── app.py                    # Streamlit Web Dashboard (The Cockpit)
└── main.py                   # Backend Pipeline Entry Point