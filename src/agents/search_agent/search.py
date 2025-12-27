"""
Module: Search Agent (Semantic Search)
Description: Performs vector similarity search against the local LanceDB instance.
             It converts natural language queries into vectors and finds the
             closest matching documents based on meaning (Cosine Similarity).
             
Usage: 
    python -m src.agents.search_agent.search "your query here"
"""

import sys
import os
from sentence_transformers import SentenceTransformer
from src.common.db import get_table

# --- CONFIGURATION ---
# Must match the model used in the Embedding Agent.
# If these don't match, the vector space will be misaligned (gibberish results).
MODEL_NAME = 'all-MiniLM-L6-v2'

def search_documents(query: str, limit: int = 5):
    """
    Executes a semantic search pipeline.
    
    Args:
        query (str): The user's search text (e.g., "tax forms 2023").
        limit (int): Max number of results to return.
    """
    print(f"🔎 Searching for: '{query}'...")
    
    # 1. Load the AI Model
    # In a persistent server (FastAPI), we would load this once at startup.
    # For CLI usage, loading it every time takes ~1-2 seconds.
    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        print(f"❌ Error loading AI model: {e}")
        return
    
    # 2. Embed the Query
    # Convert the user's text into the same 384-dimensional vector space as our docs.
    query_vector = model.encode(query)
    
    # 3. Connect to Database
    try:
        table = get_table()
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return
    
    # 4. Perform Vector Search
    # - metric="cosine": Measures the angle between vectors. 
    #   Perfect for semantic similarity (0 = identical direction, 1 = orthogonal).
    # - limit(limit): Restricts results for speed.
    # - to_pandas(): Returns the data as a clean DataFrame.
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
        # So, if Distance is 0.2, Similarity is 0.8 (80%).
        distance = row['_distance']
        similarity_score = 1 - distance
        
        # formatting: .2% converts 0.8512 to 85.12%
        print(f"📄 File: {row['filename']}")
        print(f"   📂 Path: {row['file_path']}")
        print(f"   🤖 Similarity: {similarity_score:.2%}") 
        print("-" * 60)

if __name__ == "__main__":
    # CLI Entry Point
    # Allows running: python -m src.agents.search_agent.search "my query"
    if len(sys.argv) > 1:
        # Join all arguments to handle queries with spaces without quotes
        # e.g. python ... search my passport -> "my passport"
        user_query = " ".join(sys.argv[1:])
        search_documents(user_query)
    else:
        print("Usage: python -m src.agents.search_agent.search 'your search text'")