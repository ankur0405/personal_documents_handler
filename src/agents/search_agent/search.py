"""
Module: Search Agent (Semantic Page-Level Search)
Description: 
    Performs vector similarity search against the local LanceDB instance.
    It converts natural language queries into vectors and finds the closest 
    matching *specific pages* within your documents.

Features:
    - Semantic Matching: Finds concepts, not just keywords (Cosine Similarity).
    - Page-Level Precision: Tells you exactly which page (e.g., Page 36) to open.
    - Context Snippets: Shows a preview of the actual text found.

Usage: 
    python -m src.agents.search_agent.search "your query here"
"""

import sys
import os
from sentence_transformers import SentenceTransformer
from src.common.db import get_table

# --- CONFIGURATION ---
# Must match the model used in the Embedding Agent to ensure vector alignment.
MODEL_NAME = 'all-MiniLM-L6-v2'

def search_documents(query: str, limit: int = 5):
    """
    Executes a semantic search pipeline.
    
    Args:
        query (str): The user's search text (e.g., "address in passport").
        limit (int): Max number of results to return.
    """
    print(f"🔎 Searching for: '{query}'...")
    
    # 1. Load the AI Brain
    # In a persistent app (FastAPI/Streamlit), load this once at startup.
    # For CLI, we accept the overhead of loading it per run (~1 sec).
    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        print(f"❌ Error loading AI model: {e}")
        return
    
    # 2. Embed the Query
    # Convert the user's text into the same 384-dimensional vector space 
    # as our document pages.
    try:
        query_vector = model.encode(query)
    except Exception as e:
        print(f"❌ Error encoding query: {e}")
        return
    
    # 3. Connect to Database
    try:
        table = get_table()
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return
    
    # 4. Perform Vector Search
    # - metric="cosine": Measures angular distance (meaning).
    # - limit(limit): Returns top N matches.
    results = table.search(query_vector) \
                   .metric("cosine") \
                   .limit(limit) \
                   .to_pandas()
    
    if results.empty:
        print("❌ No matches found. Try a different query.")
        return

    # 5. Display Results
    print(f"\n✅ Found {len(results)} matches:\n")
    
    for _, row in results.iterrows():
        # LanceDB returns 'distance' for Cosine metric.
        # Distance = 1 - Similarity.
        # 0.0 distance = 1.0 similarity (100% Match)
        distance = row['_distance']
        similarity_score = 1 - distance
        
        # --- RESULT CARD ---
        print(f"📄 File: {row['filename']}")
        
        # New Feature: Page Number
        # If the document is a single page (like an image), this defaults to 1.
        print(f"   📖 Page: {row['page_number']}")
        
        print(f"   📂 Path: {row['file_path']}")
        print(f"   🤖 Similarity: {similarity_score:.2%}") # Format as 85.20%
        
        # New Feature: Content Snippet
        # We show the first 150 characters of the actual text found so the user 
        # can validate if this is the right document.
        # We replace newlines with spaces for a cleaner terminal output.
        snippet = row['content'][:150].replace('\n', ' ')
        print(f"   📝 Snippet: \"{snippet}...\"")
        
        print("-" * 60)

if __name__ == "__main__":
    # CLI Entry Point
    # Example: python -m src.agents.search_agent.search "passport number"
    if len(sys.argv) > 1:
        # Join arguments to handle multi-word queries without needing quotes
        user_query = " ".join(sys.argv[1:])
        search_documents(user_query)
    else:
        print("Usage: python -m src.agents.search_agent.search 'your search text'")