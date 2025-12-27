### PROJECT STATE: Local-First AI Document Manager (v3)
**Date:** Dec 27, 2025
**Roles:** * **AI Solutions Architect:** Strategy, System Design, Constraints.
* **Lead Developer:** Implementation, Code Standards (Verbose Comments), Error Handling.

**1. Core Philosophy**
* **Local-First:** No user data (embeddings/docs) leaves the machine.
* **Privacy:** Zero-server dependency for the core loop.
* **Agentic:** Architecture designed for autonomous agents (LangGraph).
* **Code Quality:** Self-documenting code with comprehensive comments for maintainability.

**2. Hardware Profile**
* **Primary Workstation:** Mac Studio (M2 Ultra, 60-Core GPU, 192GB Unified Memory).
* **Optimization Target:** Metal Performance Shaders (MPS) for AI workloads.

**3. Architecture: The "Sidecar" Pattern**
* **Frontend:** Electron/Tauri (Desktop Wrapper).
* **Backend:** Python + FastAPI (Bundled Executable).
* **Database:** LanceDB (Embedded, Serverless Vector DB).
* **Storage Strategy:** Monorepo with single `.venv` root.

**4. Implementation details**
* **Database Schema:** Pydantic models with explicit types.
* **Scanning Logic:** `pathlib` for traversal, `xxhash` for collision-free IDs, `python-magic` for robust type detection.
* **Idempotency:** All database operations must handle "Re-runs" gracefully (Upsert logic).

**5. Roadmap**
* **Phase 1 (Complete):** Foundation (Scanner + Idempotent DB).
* **Phase 2 (Next):** Intelligence (Local Embeddings with SBERT).