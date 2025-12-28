import sys
import os
from sentence_transformers import SentenceTransformer
from src.common.db import get_table
from src.config.loader import SETTINGS

# Allow running as script or module
sys.path.append(os.getcwd())

# 1. READ MODEL FROM CONFIG
# We use the key you added to settings.yaml
MODEL_NAME = SETTINGS['system']['model_name']

def search_documents(query: str, limit: int = 5):
    """
    Embeds the query and searches the LanceDB table.
    Returns a list of dictionaries with normalized confidence scores.
    """
    try:
        # 2. Connect
        table = get_table()
        
        # 3. Embed Query using the correct Brain
        model = SentenceTransformer(MODEL_NAME)
        query_vector = model.encode([query])[0].tolist()
        
        # 4. Search
        results = table.search(query_vector).limit(limit).to_list()
        
        if not results:
            return []

        # 5. Format Results
        formatted_hits = []
        for hit in results:
            distance = hit['_distance']
            
            # Convert L2 Distance to Similarity Score (0% to 100%)
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