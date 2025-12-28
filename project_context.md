# 📂 Personal Documents Handler (Local RAG)

## 🎯 Project Vision
A privacy-first, offline AI system that indexes, reads, and searches personal documents (Passports, Tax Forms, Contracts). It runs entirely on local hardware (Apple Silicon optimized) without sending a single byte to the cloud.

---

## 🏗 System Architecture

### **The "Brain" (AI Models)**
| Component | Implementation | Specs | Role |
| :--- | :--- | :--- | :--- |
| **OCR Engine** | **PaddleOCR** (v2.7+) | `en_PP-OCRv5` | The "Eyes." Reads text from images, scans, and messy PDFs. Configured with angle classification (`cls=True`) for rotated docs. |
| **Embeddings** | **BAAI/bge-large-en-v1.5** | 1024 Dim | The "Brain." Converts text into high-dimensional vector meaning. SOTA performance (Better than OpenAI Ada-002). |
| **Vector DB** | **LanceDB** | Local Filesystem | The "Memory." Serverless, lightning-fast vector store saved to `data/lancedb_store`. |

### **The "Body" (Hardware Optimization)**
* **Target Hardware:** Apple Silicon (M2 Ultra).
* **Parallelism:** Multi-process architecture (`ProcessPoolExecutor`) with "Lane Control" to manage RAM.
* **Memory Safety:**
    * **Batching:** Strictly processes small batches (e.g., 4 files) at a time.
    * **Flushing:** Workers are recycled and `gc.collect()` is forced after every batch to create a "Sawtooth" memory usage pattern (prevents leaks).
    * **Safety Valves:** Images >2500px are auto-downscaled before OCR to prevent OOM (Out of Memory) crashes.

---

## 📂 Directory Structure

```text
personnal_documents_handler/
├── data/                       # Database storage
│   └── lancedb_store/          # LanceDB files (Vectors + Metadata)
├── src/
│   ├── agents/
│   │   ├── embedding_agent/    # The Indexing Pipeline
│   │   │   └── embedder.py     # Main logic: Extract -> Batch -> Embed -> Save
│   │   └── search_agent/       # The Retrieval Engine
│   │   │   └── search.py       # Semantic search logic
│   ├── common/
│   │   ├── db.py               # Singleton DB connection
│   │   └── factory.py          # Extractor Factory (Router)
│   ├── config/
│   │   ├── autotune.py         # Hardware detection (Eco vs God Mode)
│   │   ├── loader.py           # Config loader
│   │   └── settings.yaml       # User settings
│   ├── extractors/             # Modular File Handlers
│   │   ├── __init__.py         # Exports classes
│   │   ├── base.py             # Abstract Base Class
│   │   ├── image.py            # Computer Vision (PaddleOCR + Pre-processing)
│   │   ├── pdf.py              # Intelligent PDF (Text -> Gibberish Check -> OCR)
│   │   ├── office.py           # Word, Excel, PowerPoint
│   │   └── email.py            # Outlook .msg
│   ├── app.py                  # Streamlit UI (The "Cockpit")
│   └── main.py                 # CLI Entry Point
├── project_context.md          # You are here
└── requirements.txt            # Dependencies