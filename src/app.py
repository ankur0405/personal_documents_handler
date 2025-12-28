import streamlit as st
import pandas as pd
import time
from sentence_transformers import SentenceTransformer
from src.common.db import get_table
from src.config.loader import SETTINGS

# 1. SETUP PAGE
st.set_page_config(
    page_title="Personal Doc Search",
    page_icon="🔎",
    layout="wide"
)

# 2. LOAD BRAIN (Cached to prevent reloading on every click)
@st.cache_resource
def load_model():
    model_name = SETTINGS['system']['model_name']
    return SentenceTransformer(model_name), model_name

try:
    model, active_model_name = load_model()
except Exception as e:
    st.error(f"❌ Failed to load AI Model: {e}")
    st.stop()

# 3. SIDEBAR INFO
with st.sidebar:
    st.title("🧠 System Status")
    st.info(f"**Active Brain:**\n{active_model_name}")
    st.caption(f"Dimensions: {SETTINGS['system']['model_dimension']}")
    
    # Show DB Stats
    try:
        table = get_table()
        row_count = len(table)
        st.success(f"📚 Documents Indexed: {row_count}")
    except:
        st.warning("Database not found or empty.")

# 4. MAIN INTERFACE
st.title("🔎 Personal Document Search")
st.markdown("ask natural questions like *'What is my passport number?'* or *'Show me tax forms from 2022'*")

query = st.text_input("Enter your query:", placeholder="Type here...")

if query:
    start_time = time.time()
    
    # A. Embed Query
    query_vector = model.encode([query])[0].tolist()
    
    # B. Search Database
    try:
        table = get_table()
        # Search and limit to top 5 results
        results = table.search(query_vector).limit(5).to_list()
        
        duration = time.time() - start_time
        
        if not results:
            st.warning("No matching documents found.")
        else:
            st.subheader(f"Top Results ({duration:.2f}s)")
            
            for hit in results:
                # Calculate Confidence Score (Inverse Distance)
                distance = hit['_distance']
                score = 1 - (distance / 2) # Approximation for Cosine Distance
                
                # Visual Confidence Bar
                st.write(f"**📄 {hit['filename']}** (Page {hit['page_number']})")
                st.progress(max(0.0, min(1.0, score)), text=f"Confidence: {score:.1%}")
                
                # Content Preview (Expandable)
                with st.expander("View Content Snippet"):
                    st.markdown(f"> {hit['content']}")
                
                st.divider()
                
    except Exception as e:
        st.error(f"Search Error: {e}")