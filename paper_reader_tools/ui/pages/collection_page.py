"""
Collection page for managing reading lists.
"""
import streamlit as st

def render_page():
    """Render the view for a specific collection."""
    # Get the active collection ID
    collection_id = st.session_state.active_collection
    collection = st.session_state.api_client.get_collection(collection_id)
    
    if not collection:
        st.error("Collection not found")
        st.session_state.active_tab = "Library"
        st.session_state.need_rerun = True
        return
    
    # Display collection header and actions
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.header(f"Reading List: {collection['name']}")
    
    with col2:
        # Button to go back to library
        if st.button("← Back to Library", use_container_width=True):
            st.session_state.active_tab = "Library"
            st.session_state.need_rerun = True
            return
    
    with col3:
        # Delete button
        if st.button("🗑️ Delete List", use_container_width=True, type="secondary"):
            st.session_state.pending_action = "confirm_delete_collection"
            st.session_state.pending_collection_id = collection_id
            st.session_state.need_rerun = True
            return
    
    # Display collection description
    if collection['description']:
        st.write(collection['description'])
    
    # Show confirmation dialog if needed
    if st.session_state.get("pending_action") == "confirm_delete_collection" and st.session_state.get("pending_collection_id") == collection_id:
        st.warning(f"Are you sure you want to delete the reading list '{collection['name']}'? This cannot be undone.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", type="primary"):
                if st.session_state.api_client.delete_collection(collection_id):
                    st.success("Reading list deleted successfully!")
                    st.session_state.active_tab = "Library"
                    st.session_state.pending_action = None
                    st.session_state.pending_collection_id = None
                    st.session_state.need_rerun = True
                    return
                else:
                    st.error("Failed to delete reading list.")
        with col2:
            if st.button("Cancel"):
                st.session_state.pending_action = None
                st.session_state.pending_collection_id = None
                st.session_state.need_rerun = True
                return
    
    # Get papers in this collection
    paper_ids = collection['papers']
    paper_details = collection.get('paper_details', {})
    
    # Show message if collection is empty
    if not paper_ids:
        st.info("This reading list is empty. Add papers to get started!")
        
        # Suggest adding papers
        st.write("To add papers to this reading list:")
        st.write("1. Browse papers in the Library")
        st.write("2. Click on a paper to view its details")
        st.write("3. Click 'Add to Reading List' and select this reading list")
        return
    
    # Show papers in this collection
    st.write(f"### Papers in this reading list ({len(paper_ids)})")
    
    # Add a search/filter box for papers in the collection
    search_term = st.text_input("Filter papers in this list:", key=f"collection_filter_{collection_id}")
    
    # Get and display the papers
    displayed_papers = 0
    for paper_id in paper_ids:
        paper = st.session_state.api_client.get_paper(paper_id)
        if paper:
            # Apply filter if search term is provided
            if search_term and search_term.lower() not in paper['title'].lower() and search_term.lower() not in paper.get('authors', '').lower():
                continue
                
            displayed_papers += 1
            with st.container(border=True):
                # Get read status
                read_status = paper_details.get(str(paper_id), {}).get('read_status', False)
                
                # Paper title row with checkbox for read status
                col1, col2 = st.columns([10, 1])
                with col1:
                    st.write(f"**{paper['title']}**")
                with col2:
                    if st.checkbox("📖", value=read_status, key=f"read_status_{collection_id}_{paper_id}", 
                                 help="Mark as read"):
                        if not read_status:  # Only update if changed to read
                            if st.session_state.api_client.update_read_status(collection_id, paper_id, True):
                                st.session_state.need_rerun = True
                
                st.caption(f"Authors: {paper['authors']}")
                
                # Show tags if available
                tags = paper.get("tags", [])
                if tags:
                    st.write("Tags:", ", ".join(tags))
                
                # Add buttons for actions
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("View Paper", key=f"view_coll_paper_{paper_id}"):
                        st.session_state.current_paper_id = paper_id
                        st.session_state.active_tab = "Library"
                        st.session_state.need_rerun = True
                with col2:
                    if st.button("Remove", key=f"remove_collection_paper_{paper_id}", type="secondary"):
                        if st.session_state.api_client.remove_paper_from_collection(collection_id, paper_id):
                            st.success(f"Paper removed from {collection['name']}")
                            st.session_state.need_rerun = True
    
    # Show message if no papers match the filter
    if paper_ids and displayed_papers == 0:
        st.info(f"No papers match your filter: '{search_term}'")

def render_all_collections_page():
    """Render a view to manage all reading lists."""
    st.header("Manage Reading Lists")
    
    # Get all collections
    collections = st.session_state.api_client.get_collections()
    
    # Button to create a new reading list
    if st.button("+ Create New Reading List", type="primary"):
        st.session_state.pending_action = "show_create_collection_modal"
        st.session_state.need_rerun = True
    
    # Show existing collections
    if not collections:
        st.info("You don't have any reading lists yet. Create one to get started!")
    else:
        for collection in collections:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"### {collection['name']}")
                    st.write(f"Papers: {len(collection['papers'])}")
                    if collection.get('description'):
                        st.write(collection['description'])
                with col2:
                    # View button
                    if st.button("View", key=f"manage_view_{collection['id']}"):
                        st.session_state.active_tab = "Collection"
                        st.session_state.active_collection = collection['id']
                        st.session_state.need_rerun = True
