"""
Add paper page for uploading and processing papers.
"""
import os
import time
import tempfile
import streamlit as st

def render_page():
    """Render the add paper form."""
    st.header("Add New Paper")
    
    # Tabs for different add methods
    tab1, tab2 = st.tabs(["Upload PDF", "From URL"])
    
    with tab1:
        uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
        tags = st.text_input("Tags (comma separated)", key="upload_tags")
        
        if uploaded_file is not None:
            if st.button("Process Paper", key="upload_btn"):
                with st.spinner("Uploading and processing paper..."):
                    # Create a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        # Upload the temporary file
                        with open(tmp_path, "rb") as f:
                            response = st.session_state.api_client.upload_paper(f, tags)
                        
                        if response and "task_id" in response:
                            st.session_state.current_task = response["task_id"]
                            st.rerun()
                    finally:
                        # Clean up
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
    
    with tab2:
        url = st.text_input("Enter PDF URL", key="pdf_url")
        url_tags = st.text_input("Tags (comma separated)", key="url_tags")
        
        if st.button("Process URL", key="url_btn"):
            if not url.strip():
                st.error("Please enter a URL")
            elif not url.lower().endswith(".pdf"):
                st.error("URL must point to a PDF file")
            else:
                with st.spinner("Processing URL..."):
                    tag_list = [tag.strip() for tag in url_tags.split(',') if tag.strip()]
                    response = st.session_state.api_client.process_url(url, tag_list)
                    if response and "task_id" in response:
                        st.session_state.current_task = response["task_id"]
                        st.rerun()
    
    # Check if there's an ongoing task
    if st.session_state.current_task:
        render_processing_status()

def render_processing_status():
    """Render the processing status with progress bar."""
    st.subheader("Processing Paper")
    
    status_container = st.container()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Check status every 2 seconds
    while True:
        status = st.session_state.api_client.check_task_status(st.session_state.current_task)
        
        if status.get("status") == "processing":
            progress = status.get("progress", 0)
            progress_bar.progress(progress / 100)
            
            # Update status text based on progress
            if progress < 25:
                status_text.text("Extracting paper content...")
            elif progress < 50:
                status_text.text("Analyzing paper structure...")
            elif progress < 75:
                status_text.text("Generating AI summary...")
            else:
                status_text.text("Creating the final report...")
                
        elif status.get("status") == "complete":
            progress_bar.progress(100)
            status_text.success("Processing complete!")
            
            # Redirect to the paper details
            if "paper_id" in status:
                time.sleep(1)  # Brief pause for user to see success message
                st.session_state.current_paper_id = status["paper_id"]
                st.session_state.active_tab = "Library"
                st.session_state.current_task = None
                st.rerun()
            break
            
        elif status.get("status") == "failed":
            progress_bar.empty()
            status_text.error(f"Processing failed: {status.get('error', 'Unknown error')}")
            # Add a button to try again
            if st.button("Start Over"):
                st.session_state.current_task = None
                st.rerun()
            break
            
        elif status.get("status") == "not_found":
            progress_bar.empty()
            status_text.warning("Task not found. It may have expired.")
            # Add a button to try again
            if st.button("Start Over"):
                st.session_state.current_task = None
                st.rerun()
            break
        
        # Wait before checking status again
        time.sleep(2)
