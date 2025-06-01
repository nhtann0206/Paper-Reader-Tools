"""
About page showing information about the application.
"""
import streamlit as st

def render_page():
    """Render the about page."""
    st.header("About Paper Reader Tools")
    
    st.write("""
    Paper Reader Tools is an application that helps researchers and students 
    efficiently process, summarize, and organize research papers.
    
    ### Features:
    - Extract text from PDF research papers
    - Use Google's Gemini 2.0 Flash AI to generate comprehensive summaries
    - Organize papers with tags
    - Search for papers by keywords or concepts
    - Download formatted summaries as PDFs
    
    ### How It Works:
    1. Upload a PDF file or provide a URL to a research paper
    2. The system extracts the text and identifies key sections
    3. The AI generates a summary of the paper
    4. The summary and metadata are stored for easy reference
    5. You can access your papers from the library at any time
    
    ### Technology:
    - Backend: FastAPI + Async Python
    - Frontend: Streamlit
    - AI: Google Gemini 2.0 Flash
    - Vector Search: Sentence Transformers
    """)
    
    st.divider()
    
    st.write("Created by nhtann_0206, last updated on 2023-05-30")
    st.write("This project is open source and available on [GitHub](https://github.com/nhtann0206/Paper-reader-tools)")
    st.caption("Version 0.1.0")
