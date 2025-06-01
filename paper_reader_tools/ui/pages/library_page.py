"""
Library page for displaying papers and paper details.
"""
import os
import base64
import streamlit as st
import streamlit.components.v1 as components
import requests
from typing import Dict, List, Any

def render_page():
    """Render the library page with paper list and details."""
    # Check if we need to show PDF viewer
    if "view_pdf" in st.query_params and "paper_id" in st.query_params:
        paper_id = int(st.query_params["paper_id"])
        show_pdf_viewer(paper_id=paper_id)
        return
    
    # Get papers, optionally filtered by tag
    filter_tag = st.session_state.get("current_tag")
    papers = st.session_state.api_client.get_papers(tag=filter_tag)
    
    # Split the view into two columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Your Papers")
        if not papers:
            st.info("No papers found. Add some papers to get started!")
        else:
            # Create a list of papers
            for paper in papers:
                paper_title = paper.get("title", "Untitled Paper")
                paper_authors = paper.get("authors", "Unknown Authors")
                paper_id = paper.get("id")
                
                # Use a container for each paper
                with st.container(border=True):
                    st.write(f"**{paper_title}**")
                    st.caption(paper_authors)
                    
                    # Show tags if available
                    tags = paper.get("tags", [])
                    if tags:
                        st.write(" ".join([f":{tag.lower()}:" for tag in tags[:3]]))
                    
                    # Button to view paper details
                    if st.button("View", key=f"view_{paper_id}"):
                        st.session_state.current_paper_id = paper_id
                        st.session_state.need_rerun = True
    
    with col2:
        # Show paper details or welcome message
        if st.session_state.current_paper_id:
            render_paper_details(st.session_state.current_paper_id)
        else:
            st.subheader("Paper Reader")
            st.write("Select a paper from the list to view its details.")

def render_paper_details(paper_id: int):
    """Render the details of a specific paper."""
    paper = st.session_state.api_client.get_paper(paper_id)
    
    if not paper:
        st.error("Paper not found")
        return
    
    # Paper title and metadata
    st.header(paper.get("title", "Untitled Paper"))
    
    # Authors and publication info
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Authors:** {paper.get('authors', 'Unknown')}")
        if paper.get("publication"):
            st.write(f"**Publication:** {paper.get('publication')}")
    with col2:
        if paper.get("publication_date"):
            st.write(f"**Date:** {paper.get('publication_date')}")
        if paper.get("url"):
            st.write(f"**Source:** [Link]({paper.get('url')})")
    
    # Display tags
    tags = paper.get("tags", [])
    if tags:
        st.write("**Tags:**", ", ".join(tags))
    
    # PDF actions row
    if paper.get("output_path"):
        pdf_filename = paper.get("output_path")
        
        # API URL for requests made from within the Streamlit app
        api_pdf_url = f"{st.session_state.api_client.api_url}/output/{pdf_filename}"
        
        # Generate browser-accessible URLs by replacing Docker hostnames with localhost
        # This handles both development and production environments
        pdf_view_url = api_pdf_url.replace("http://api:8080", "http://localhost:8080")
        
        # PDF actions in 3 buttons laid out horizontally
        st.write("### PDF Actions:")
        btn1, btn2, btn3 = st.columns(3)
        
        # Button 1: View PDF in app
        with btn1:
            if st.button("📄 View in App", key="view_pdf_btn"):
                st.query_params["view_pdf"] = "true"
                st.query_params["paper_id"] = str(paper_id)
                st.rerun()
        
        # Button 2: Download PDF
        with btn2:
            try:
                # Just show the button; it'll handle its own download
                st.download_button(
                    label="⬇️ Download PDF",
                    data=requests.get(api_pdf_url, timeout=10).content,  # Use API URL for internal requests
                    file_name=pdf_filename,
                    mime="application/pdf",
                    key="download_pdf_btn"
                )
            except Exception as e:
                st.warning(f"Download unavailable: {str(e)}")
                
        # Button 3: Open in new tab with browser-accessible URL
        with btn3:
            # Enhanced button styling with gradient, shadow, and hover effect
            js_code = f"""
            <a href="{pdf_view_url}" target="_blank" rel="noopener noreferrer"
               style="display:inline-block; width:100%; text-align:center; 
                      padding:0.6rem 0.8rem; border-radius:6px; font-weight:500;
                      color:white; text-decoration:none; 
                      background: linear-gradient(135deg, #4CAF50, #2E7D32);
                      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                      transition: all 0.2s ease-in-out;
                      border: none; cursor: pointer;"
               onmouseover="this.style.transform='scale(1.02)';this.style.boxShadow='0 4px 8px rgba(0,0,0,0.3)';"
               onmouseout="this.style.transform='scale(1)';this.style.boxShadow='0 2px 4px rgba(0,0,0,0.2)';">
               <span style="display:inline-flex; align-items:center; justify-content:center;">
                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" style="margin-right:6px;">
                   <path fill-rule="evenodd" d="M8.636 3.5a.5.5 0 0 0-.5-.5H1.5A1.5 1.5 0 0 0 0 4.5v10A1.5 1.5 0 0 0 1.5 16h10a1.5 1.5 0 0 0 1.5-1.5V7.864a.5.5 0 0 0-1 0V14.5a.5.5 0 0 1-.5.5h-10a.5.5 0 0 1-.5-.5v-10a.5.5 0 0 1 .5-.5h6.636a.5.5 0 0 0 .5-.5z"/>
                   <path fill-rule="evenodd" d="M16 .5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793L6.146 9.146a.5.5 0 1 0 .708.708L15 1.707V5.5a.5.5 0 0 0 1 0v-5z"/>
                 </svg>
                 Open in New Tab
               </span>
            </a>
            """
            st.components.v1.html(js_code, height=40)
    
    # Collection actions in a separate row
    st.write("### Actions:")
    action1, action2 = st.columns(2)
    
    with action1:
        if st.button("Add to Reading List", key="add_to_list_btn", use_container_width=True):
            st.session_state.show_collection_select = True
            st.session_state.current_paper_for_collection = paper_id
            st.rerun()
    
    with action2:
        if st.button("Delete Paper", key="delete_paper_btn", use_container_width=True, type="primary"):
            if st.session_state.api_client.delete_paper(paper_id):
                st.session_state.current_paper_id = None
                st.success("Paper deleted successfully!")
                st.session_state.need_rerun = True
            else:
                st.error("Failed to delete paper.")
    
    # Show collection selection if flag is set
    if st.session_state.get("show_collection_select", False) and st.session_state.get("current_paper_for_collection") == paper_id:
        st.write("### Select a reading list:")
        collections = st.session_state.api_client.get_collections()
        
        if collections:
            options = ["Create new..."] + [c['name'] for c in collections]
            selected = st.selectbox("Reading List:", options, key="collection_select_box")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Add", key="confirm_add_to_collection"):
                    if selected == "Create new...":
                        st.session_state.pending_action = "show_create_collection_modal"
                        st.session_state.need_rerun = True
                    else:
                        # Find collection ID by name
                        collection = next((c for c in collections if c['name'] == selected), None)
                        if collection and st.session_state.api_client.add_paper_to_collection(collection['id'], paper_id):
                            st.success(f"Added to '{selected}'!")
                            st.session_state.show_collection_select = False
                            st.session_state.need_rerun = True
                        else:
                            st.error("Failed to add to reading list")
            with col2:
                if st.button("Cancel", key="cancel_add_to_collection"):
                    st.session_state.show_collection_select = False
                    st.session_state.need_rerun = True
        else:
            st.warning("You don't have any reading lists. Create one first?")
            if st.button("Create New Reading List"):
                st.session_state.pending_action = "show_create_collection_modal"
                st.session_state.need_rerun = True
    
    # Summary content
    st.subheader("Summary")
    st.markdown(paper.get("summary", "No summary available."), unsafe_allow_html=True)

def render_collection_modal():
    """Render modal to create a new collection."""
    st.write("### Create New Reading List")
    
    with st.form("create_collection_form"):
        name = st.text_input("Name")
        description = st.text_area("Description")
        
        # Form submission buttons
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Create")
        with col2:
            cancel = st.form_submit_button("Cancel")
        
        if submit and name:
            collection = st.session_state.api_client.create_collection(name, description)
            if collection:
                st.success(f"Reading List '{name}' created!")
                
                # Add current paper to the collection if we're in that context
                if st.session_state.get("current_paper_for_collection"):
                    paper_id = st.session_state.current_paper_for_collection
                    st.session_state.api_client.add_paper_to_collection(
                        collection['id'], paper_id
                    )
                    st.success(f"Paper added to '{name}'!")
                
                # Reset all pending actions
                st.session_state.pending_action = None
                st.session_state.show_collection_select = False
                st.session_state.current_paper_for_collection = None
                st.session_state.need_rerun = True
            else:
                st.error("Failed to create reading list")
        
        if cancel:
            st.session_state.pending_action = None
            st.session_state.show_collection_select = False
            st.session_state.current_paper_for_collection = None
            st.session_state.need_rerun = True

def show_pdf_viewer(paper_id: int = None, pdf_url: str = None):
    """
    Display a PDF viewer in the Streamlit app.
    Either paper_id or pdf_url must be provided.
    """
    st.header("PDF Viewer")
    
    # Add a close button at the top
    if st.button("← Back to Paper"):
        # Clear the query params and return to the paper view
        st.query_params.clear()
        st.rerun()
    
    # If we have a paper_id, get the paper details
    if paper_id:
        paper = st.session_state.api_client.get_paper(paper_id)
        if not paper or not paper.get("output_path"):
            st.error("Document not found")
            return
        
        file_path = paper.get("output_path")
        output_url = f"{st.session_state.api_client.api_url}/pdf/{file_path}"
    else:
        # Use the direct URL
        output_url = pdf_url
        file_path = output_url.split("/")[-1]
    
    try:
        # Fix URL for browser access
        output_url_for_browser = output_url.replace("http://api:8080", "http://localhost:8080")
        
        # Display buttons for opening/downloading at the top
        col1, col2 = st.columns(2)
        
        with col1:
            # Enhanced "Open in New Tab" button with better styling
            html_button = f"""
            <a href='{output_url_for_browser}' target='_blank' 
               style="display:inline-block; width:100%; text-align:center; 
                      padding:0.7rem 1rem; border-radius:6px; font-weight:500;
                      color:white; text-decoration:none; 
                      background: linear-gradient(135deg, #1E88E5, #1565C0);
                      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                      transition: all 0.2s ease-in-out;
                      border: none; cursor: pointer;"
               onmouseover="this.style.transform='scale(1.02)';this.style.boxShadow='0 4px 8px rgba(0,0,0,0.3)';"
               onmouseout="this.style.transform='scale(1)';this.style.boxShadow='0 2px 4px rgba(0,0,0,0.2)';">
               <span style="display:inline-flex; align-items:center; justify-content:center;">
                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" style="margin-right:8px;">
                   <path fill-rule="evenodd" d="M8.636 3.5a.5.5 0 0 0-.5-.5H1.5A1.5 1.5 0 0 0 0 4.5v10A1.5 1.5 0 0 0 1.5 16h10a1.5 1.5 0 0 0 1.5-1.5V7.864a.5.5 0 0 0-1 0V14.5a.5.5 0 0 1-.5.5h-10a.5.5 0 0 1-.5-.5v-10a.5.5 0 0 1 .5-.5h6.636a.5.5 0 0 0 .5-.5z"/>
                   <path fill-rule="evenodd" d="M16 .5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793L6.146 9.146a.5.5 0 1 0 .708.708L15 1.707V5.5a.5.5 0 0 0 1 0v-5z"/>
                 </svg>
                 Open in New Tab
               </span>
            </a>
            """
            st.components.v1.html(html_button, height=45)
            
        with col2:
            # Matching style for the download button
            html_download = f"""
            <a href='{output_url_for_browser}' download
               style="display:inline-block; width:100%; text-align:center; 
                      padding:0.7rem 1rem; border-radius:6px; font-weight:500;
                      color:white; text-decoration:none; 
                      background: linear-gradient(135deg, #FF9800, #F57C00);
                      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                      transition: all 0.2s ease-in-out;
                      border: none; cursor: pointer;"
               onmouseover="this.style.transform='scale(1.02)';this.style.boxShadow='0 4px 8px rgba(0,0,0,0.3)';"
               onmouseout="this.style.transform='scale(1)';this.style.boxShadow='0 2px 4px rgba(0,0,0,0.2)';">
               <span style="display:inline-flex; align-items:center; justify-content:center;">
                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" style="margin-right:8px;">
                   <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                   <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
                 </svg>
                 Download
               </span>
            </a>
            """
            st.components.v1.html(html_download, height=45)
        
        st.divider()
        
        # Download the file from the API
        response = requests.get(output_url)
        response.raise_for_status()
        file_content = response.content
        
        # Check if it's a markdown file
        is_markdown = file_path.lower().endswith('.md')
        
        if is_markdown:
            # Display markdown content directly
            st.subheader("Paper Summary")
            markdown_text = file_content.decode('utf-8')
            st.markdown(markdown_text)
        else:
            # It's a PDF - display it using available methods
            st.subheader("PDF Document")
            
            try:
                # Try native PDF viewer first (newer Streamlit versions)
                st.pdf_viewer(file_content, width=800)
                st.success("PDF loaded successfully")
            except Exception as e:
                # Fall back to base64 iframe approach
                try:
                    st.warning("Using fallback PDF viewer")
                    b64_pdf = base64.b64encode(file_content).decode('utf-8')
                    pdf_display = f"""
                    <iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="800px" 
                            style="border: none; border-radius: 5px;">This browser does not support PDFs. Please download the PDF to view it.</iframe>
                    """
                    st.markdown(pdf_display, unsafe_allow_html=True)
                except Exception as e2:
                    st.error(f"Failed to display PDF: {str(e2)}")
                    st.info("Please use the links above to open or download the PDF.")
    
    except Exception as e:
        st.error(f"Error displaying document: {str(e)}")
        # Use the browser-accessible URL here too
        st.markdown(f"Try opening the document directly: [Open PDF]({output_url.replace('http://api:8080', 'http://localhost:8080')})")
