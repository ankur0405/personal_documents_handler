# Project Context: Intelligent Document Chatbot

## Project Vision
To create a conversational agent ("Chatbox") that allows users to interact with their personal document repository (Visas, Tax Docs, Legal). Unlike simple search, this system maintains chat context, understands document categories, and performs intelligent reasoning (e.g., "latest" vs. "oldest", identifying missing documents).

## Architecture Overview

### 1. The "Smart" Ingestion Pipeline
We are moving away from simple chunking to a three-step parallel process:
* **Categorization:** Classify documents (e.g., "Visa", "Tax Return", "Insurance") before embedding.
* **Metadata Extraction:** Extract structured fields (Dates, Country, Page Numbers) to enable filtering and sorting.
* **Summarization:** Generate document-level summaries for high-level Q&A.

### 2. Storage Strategy
* **Vector Store:** Stores text embeddings.
* **Metadata Store:** Stores rich JSON payloads alongside vectors (e.g., `{ "date": "2025-12-12", "category": "Visa" }`) to enable "Self-Querying" (filtering by date/type).

### 3. Retrieval & Interaction
* **Hybrid Search:** Combines semantic similarity (text match) with metadata filtering (e.g., `WHERE category = 'Visa' ORDER BY date DESC`).
* **Conversational Memory:** The system retains session context. If the user asks "When does it expire?" after viewing a document, the system resolves "it" to the previously retrieved document.
* **Gap Analysis (Future):** Ability to check for missing documents based on category counts (e.g., "Missing Flight Ticket").

## Current Implementation Roadmap
1.  **Refine Ingestion (Active):** Implement Metadata Extraction and Categorization logic.
2.  **Re-Embed:** Re-process documents with the new metadata schema.
3.  **Self-Querying Retriever:** Implement the logic to translate natural language ("latest visa") into structured DB queries.
4.  **Chat Interface:** Build the session loop with history retention.

## Key Technical Decisions
* **Embeddings:** Re-initiating to include metadata.
* **Search Type:** Self-Querying / Hybrid Search.
* **Context:** Session-based (Conversational History).