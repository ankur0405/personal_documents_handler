import sys
import os
from sentence_transformers import SentenceTransformer
from src.common.db import get_table

# Allow running as script or module
sys.path.append(os.getcwd())

MODEL_NAME = 'all-MiniLM-L6-v2'

def search_documents(query: str, limit: int = 5):
    """
    Embeds the query and searches the LanceDB table.
    Returns a list of dictionaries with normalized confidence scores.
    """
    try:
        # 1. Connect
        table = get_table()
        
        # 2. Embed Query
        model = SentenceTransformer(MODEL_NAME)
        query_vector = model.encode([query])[0].tolist()
        
        # 3. Search
        # LanceDB returns a list of dictionaries directly
        results = table.search(query_vector).limit(limit).to_list()
        
        if not results:
            return []

        # 4. Format Results with Proper Scoring
        formatted_hits = []
        for hit in results:
            distance = hit['_distance']
            
            # --- SCORING MATH FIX ---
            # LanceDB default is L2 Distance (0 is perfect, >1 is far).
            # We convert this to a Similarity Score (0% to 100%).
            # Formula: 1 / (1 + distance)
            score = 1 / (1 + distance)
            
            formatted_hits.append({
                'filename': hit['filename'],
                'file_path': hit['file_path'],
                'page_number': hit['page_number'],
                'content': hit['content'],
                'score': score
            })
            
        return formatted_hits

    except Exception as e:
        print(f"❌ Search Error: {e}")
        return []

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = sys.argv[1]
        hits = search_documents(q)
        for h in hits:
            print(f"Found: {h['filename']} (Score: {h['score']:.2%})")
    else:
        print("Usage: python -m src.agents.search_agent.search 'your query'")