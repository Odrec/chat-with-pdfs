"""
Reusable UI components for the Chat with Docs application.
"""

import os
import streamlit as st
import ast
import fitz  # PyMuPDF

from ..utils.logger import Logger

def display_document_info(file_name: str) -> None:
    """Display metadata information for the current document."""
    if file_name not in st.session_state.pdf_data:
        st.warning("Document information not available")
        return
    
    # Get document ID
    doc_id = st.session_state.file_document_id.get(file_name)
    if not doc_id:
        st.warning("Document ID not found")
        return
    
    # Find metadata from the vector index
    vector_index = st.session_state.pdf_data[file_name].get('vector_index')
    if not vector_index or not vector_index.docstore:
        st.warning("Document data not found")
        return
    
    # Get a representative node to extract metadata
    try:
        metadata = _extract_document_metadata(vector_index)
        if not metadata:
            raise ValueError("Could not extract metadata")
    except Exception as e:
        st.warning(f"Could not retrieve document metadata: {str(e)}")
        return
    
    # Display formatted metadata
    st.subheader("Document Information")
    
    # Title
    if metadata.get('title') and metadata['title'] not in ['None', 'null']:
        st.markdown(f"**Title:** {metadata['title']}")
    
    # Author
    if metadata.get('author') and metadata['author'] not in ['None', 'null']:
        st.markdown(f"**Author:** {metadata['author']}")
    
    # Keywords
    if metadata.get('keywords') and metadata['keywords'] not in ['None', 'null']:
        st.markdown(f"**Keywords:** {metadata['keywords']}")
    
    # Display summary if available
    if doc_id and doc_id in st.session_state.get('document_summaries', {}):
        st.markdown("### Summary")
        summary = st.session_state['document_summaries'][doc_id]
        st.markdown(f"{summary}")
        st.markdown("---")
    
    # Page count - get from the PDF path if available
    pdf_path = st.session_state.pdf_data[file_name].get('path')
    if pdf_path and os.path.exists(pdf_path):
        try:
            doc = fitz.open(pdf_path)
            st.markdown(f"**Page count:** {len(doc)}")
            doc.close()
        except Exception as e:
            Logger.warning(f"Could not determine page count: {str(e)}")
    
    # Table of Contents
    if metadata.get('toc_items') and metadata['toc_items'] not in ['None', 'null', '[]']:
        st.markdown("**Table of Contents:**")
        try:
            # Safely evaluate the toc_items string
            toc_items = ast.literal_eval(metadata['toc_items'])
            if isinstance(toc_items, list) and toc_items:
                for item in toc_items:
                    if isinstance(item, dict) and 'title' in item and 'page' in item:
                        st.markdown(f"- {item['title']} (Page {item['page']})")
        except Exception as e:
            # Fallback to displaying the raw string
            st.markdown(metadata['toc_items'])


def display_document_images(file_name: str) -> None:
    """Display all images extracted from the document."""
    if file_name not in st.session_state.pdf_data:
        st.warning("Document images not available")
        return
    
    # Get document ID
    doc_id = st.session_state.file_document_id.get(file_name)
    if not doc_id:
        st.warning("Document ID not found")
        return
    
    # Get image paths for this document
    image_paths = st.session_state.get('document_image_map', {}).get(doc_id, [])
    
    if not image_paths:
        st.info("No images found in this document")
        return
    
    st.subheader(f"Images from {file_name}")
    st.caption(f"Found {len(image_paths)} images")
    
    # Create a grid layout for images (3 columns)
    cols = st.columns(3)
    
    # Display images in a grid
    for i, img_path in enumerate(image_paths):
        # Check if image exists
        if os.path.exists(img_path):
            # Extract page number from filename (format: filename-page-index.jpg)
            page_num = "Unknown"
            try:
                # Pattern is usually: filename-page-index.jpg
                parts = os.path.basename(img_path).split('-')
                if len(parts) >= 2:
                    page_part = parts[-2]
                    page_num = int(page_part) + 1  # Convert to 1-based page number
            except Exception as e:
                Logger.warning(f"Could not extract page number from {img_path}: {e}")
            
            try:
                # Read the image file as binary data
                with open(img_path, 'rb') as f:
                    img_bytes = f.read()
                
                # Display image in the appropriate column using binary data
                with cols[i % 3]:
                    st.image(img_bytes, caption=f"Page {page_num}")
                    st.caption(f"Image {i+1} of {len(image_paths)}")
            except Exception as e:
                with cols[i % 3]:
                    Logger.error(f"Error displaying image {img_path}: {e}")
                    st.warning(f"Error displaying image: {os.path.basename(img_path)}")
        else:
            with cols[i % 3]:
                Logger.warning(f"Image file not found: {img_path}")
                st.warning(f"Image file not found: {os.path.basename(img_path)}")


def _extract_document_metadata(vector_index):
    """Helper function to extract metadata from a vector index.
    
    Args:
        vector_index: The vector index containing document metadata
        
    Returns:
        dict: Document metadata or None if not found
    """
    # Extract based on docstore API structure
    try:
        # Try to get documents using the docstore API
        # First attempt: use get_all() method if available
        if hasattr(vector_index.docstore, 'get_all'):
            all_documents = vector_index.docstore.get_all()
            if all_documents:
                first_node_id = list(all_documents.keys())[0]
                first_node = all_documents[first_node_id]
                return first_node.metadata
            
        # Second attempt: for newer versions with docs dictionary
        elif hasattr(vector_index.docstore, 'docs'):
            if vector_index.docstore.docs:
                first_node_id = list(vector_index.docstore.docs.keys())[0]
                first_node = vector_index.docstore.docs[first_node_id]
                return first_node.metadata
            
        # Third attempt: get document IDs and fetch first document
        elif hasattr(vector_index.docstore, 'get_document_ids'):
            doc_ids = vector_index.docstore.get_document_ids()
            if doc_ids:
                first_node_id = doc_ids[0]
                first_node = vector_index.docstore.get_document(first_node_id)
                return first_node.metadata
            
        # Fallback method - try to get documents from the index
        elif hasattr(vector_index, 'ref_docs'):
            ref_docs = vector_index.ref_docs
            if ref_docs:
                first_node = list(ref_docs.values())[0]
                return first_node.metadata
    except Exception as e:
        Logger.error(f"Error extracting metadata: {str(e)}")
    
    return None