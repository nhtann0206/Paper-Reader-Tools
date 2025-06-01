"""
Search page for finding papers.
"""
import pandas as pd
import streamlit as st

def render_page():
    """Render the search results page."""
    st.header("Search Papers")
    
    # Add search field in the main content area as well
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search for papers:", 
                                    value=st.session_state.search_query,
                                    placeholder="Enter keywords to search...")
    with col2:
        if st.button("Search", use_container_width=True):
            st.session_state.search_query = search_query
            st.session_state.need_rerun = True
    
    st.info("Search for paper titles, authors, or content. Use the search box above or in the sidebar.")
    
    query = st.session_state.search_query
    if not query:
        st.write("Enter a search term and click Search to find papers.")
        return
    
    st.write(f"Searching for: **{query}**")
    
    # Display a spinner while searching
    with st.spinner(f"Searching for '{query}'..."):
        # Perform search from previous run
        results = st.session_state.api_client.search_papers(query)
    
    if not results:
        st.info("No papers found matching your search.")
        return
    
    # Display number of results
    st.write(f"Found {len(results)} papers matching your query.")
    
    # Display results in a table
    papers_data = []
    for paper in results:
        papers_data.append({
            "ID": paper.get("id"),
            "Title": paper.get("title", "Untitled Paper"),
            "Authors": paper.get("authors", "Unknown"),
            "Tags": ", ".join(paper.get("tags", [])),
        })
    
    df = pd.DataFrame(papers_data)
    
    # Create a grid with clickable rows
    for i, row in df.iterrows():
        with st.container(border=True):
            st.write(f"**{row['Title']}**")
            st.write(f"By: {row['Authors']}")
            if row['Tags']:
                st.caption(f"Tags: {row['Tags']}")
            
            if st.button("View Paper", key=f"search_result_{row['ID']}"):
                st.session_state.current_paper_id = row['ID']
                st.session_state.active_tab = "Library"
                st.session_state.need_rerun = True
