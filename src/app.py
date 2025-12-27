import streamlit as st
import os
import sys

# Ensure we can find 'src' modules
sys.path.append(os.getcwd())

from src.agents.search_agent.search import search_documents

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="My Doc Search", 
    page_icon="🔍", 
    layout="wide"
)

# --- CUSTOM CSS (Optional Clean-up) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #FAFAFA; }
    .stExpander { border: 1px solid #303030; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col1, col2 = st.columns([1, 5])
with col1:
    st.title("🧠") 
with col2:
    st.title("Personal Knowledge Base")
    st.caption("Search across PDFs, Emails, Images, and Slides.")

st.divider()

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("⚙️ Settings")
    limit = st.slider("Max Results", min_value=1, max_value=20, value=5)
    
    st.markdown("---")
    st.info("📂 **Connected Source:**\n`/Volumes/Extreme SSD/Documents`")
    st.caption("Powered by LanceDB & MiniLM")

# --- MAIN SEARCH BAR ---
query = st.text_input("What are you looking for?", placeholder="e.g., Passport number, Tax deductions 2023, Project plan...")

if query:
    with st.spinner("Searching neural index..."):
        results = search_documents(query, limit=limit)

    if not results:
        st.warning(f"No documents found matching '{query}'.")
    else:
        # st.success(f"Found {len(results)} matches.")
        
        for i, hit in enumerate(results):
            score = hit['score']
            
            # Dynamic Icon based on file type
            icon = "📄"
            if hit['file_path'].endswith(('.jpg', '.png', '.jpeg')): icon = "🖼️"
            elif hit['file_path'].endswith('.msg'): icon = "📧"
            elif hit['file_path'].endswith('.pptx'): icon = "📊"
            elif hit['file_path'].endswith(('.xlsx', '.csv')): icon = "📈"

            # Expander Card
            with st.expander(f"{icon} {hit['filename']} (Page {hit['page_number']})  —  Confidence: {score:.2%}", expanded=(i==0)):
                
                c1, c2 = st.columns([3, 2])
                
                with c1:
                    st.markdown("### 📝 Text Snippet")
                    st.info(hit['content'])
                    st.caption(f"📍 Path: `{hit['file_path']}`")
                
                with c2:
                    # Image Preview Logic
                    if hit['file_path'].lower().endswith(('.jpg', '.png', '.jpeg', '.heic')):
                        if os.path.exists(hit['file_path']):
                            st.image(hit['file_path'], caption="Live Preview", use_container_width=True)
                        else:
                            st.error("Image file missing from disk.")
                    else:
                        st.markdown(f"""
                        <div style="
                            border: 2px dashed #444; 
                            border-radius: 10px; 
                            padding: 40px; 
                            text-align: center; 
                            color: #666;">
                            Preview not available for {icon}
                        </div>
                        """, unsafe_allow_html=True)