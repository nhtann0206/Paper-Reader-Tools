"""
Streamlit frontend entry point for Paper Reader Tools.
"""
import os
import streamlit as st

# Fix imports to work in Docker container - using absolute imports
from paper_reader_tools.ui.api_client import APIClient
from paper_reader_tools.ui.pages import (
    library_page, 
    add_paper_page, 
    search_page, 
    collection_page,
    about_page
)

# API settings
API_URL = os.environ.get("API_URL", "http://localhost:8080")

# App title and configuration
st.set_page_config(
    page_title="Paper Reader Tools",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = True  # For now, assume authenticated
    if "current_paper_id" not in st.session_state:
        st.session_state.current_paper_id = None
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "current_task" not in st.session_state:
        st.session_state.current_task = None
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Library"
    if "active_collection" not in st.session_state:
        st.session_state.active_collection = None
    if "need_rerun" not in st.session_state:
        st.session_state.need_rerun = False
    if "pending_action" not in st.session_state:
        st.session_state.pending_action = None
    if "pending_collection_id" not in st.session_state:
        st.session_state.pending_collection_id = None
    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient(API_URL)
    # New session state variables for collection selection
    if "show_collection_select" not in st.session_state:
        st.session_state.show_collection_select = False
    if "current_paper_for_collection" not in st.session_state:
        st.session_state.current_paper_for_collection = None

def render_sidebar():
    """Render the sidebar with navigation options."""
    with st.sidebar:
        st.title("Paper Reader Tools")
        
        # Navigation tabs
        st.subheader("Navigation")
        tabs = ["Library", "Add Paper", "Search", "Reading Lists", "About"]
        
        for tab in tabs:
            if st.button(tab, use_container_width=True, 
                       key=f"nav_{tab}", 
                       type="primary" if st.session_state.active_tab == tab else "secondary"):
                st.session_state.active_tab = tab
                if tab == "Library":
                    st.session_state.current_paper_id = None
                st.session_state.pending_action = None
                st.session_state.need_rerun = True
        
        # Add search box in sidebar when in search tab
        if st.session_state.active_tab == "Search":
            st.subheader("Search Papers")
            search_query = st.text_input("Enter search term:", value=st.session_state.search_query, key="sidebar_search")
            if st.button("Search", key="search_btn", use_container_width=True):
                st.session_state.search_query = search_query
                st.session_state.need_rerun = True
        
        # Tag filtering if in Library tab
        if st.session_state.active_tab == "Library":
            st.subheader("Filter by Tag")
            all_tags = st.session_state.api_client.get_all_tags()
            selected_tag = st.selectbox("Select tag", ["All"] + all_tags, key="tag_filter")
            
            filter_tag = selected_tag if selected_tag != "All" else None
            
            if "current_tag" not in st.session_state:
                st.session_state.current_tag = filter_tag
            elif st.session_state.current_tag != filter_tag:
                st.session_state.current_tag = filter_tag
                st.session_state.current_paper_id = None
                st.session_state.need_rerun = True
            
            # Reading Lists section
            st.subheader("Reading Lists")
            collections = st.session_state.api_client.get_collections()
            
            # Add a button to create new reading list
            if st.button("+ New Reading List", key="new_collection_btn", use_container_width=True):
                st.session_state.pending_action = "show_create_collection_modal"
                st.session_state.need_rerun = True
            
            # Show existing collections if there are any
            if collections:
                for collection in collections:
                    if st.button(
                        f"{collection['name']} ({len(collection['papers'])})",
                        key=f"collection_{collection['id']}",
                        use_container_width=True
                    ):
                        st.session_state.active_tab = "Collection"
                        st.session_state.active_collection = collection['id']
                        st.session_state.need_rerun = True

def handle_pending_actions():
    """Handle any pending actions from callbacks."""
    if st.session_state.pending_action == "show_create_collection_modal":
        library_page.render_collection_modal()
        st.session_state.pending_action = None

def main():
    """Main Streamlit application."""
    # Initialize session state
    init_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Handle pending actions
    handle_pending_actions()
    
    # Handle any potential rerun requests
    if st.session_state.need_rerun:
        st.session_state.need_rerun = False
        st.rerun()
    
    # Render the current tab
    if st.session_state.active_tab == "Library":
        library_page.render_page()
    elif st.session_state.active_tab == "Add Paper":
        add_paper_page.render_page()
    elif st.session_state.active_tab == "Search":
        search_page.render_page()
    elif st.session_state.active_tab == "Collection":
        collection_page.render_page()
    elif st.session_state.active_tab == "Reading Lists":
        collection_page.render_all_collections_page()
    elif st.session_state.active_tab == "About":
        about_page.render_page()

if __name__ == "__main__":
    main()