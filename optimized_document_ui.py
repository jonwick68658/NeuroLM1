#!/usr/bin/env python3
"""
Optimized Document UI Integration
Replaces slow document processing with batch operations and progress tracking
"""

import streamlit as st
from file_processor import DocumentProcessor
from optimized_document_processor import OptimizedDocumentProcessor, estimate_processing_time

def optimized_document_upload_section(user_id: str, memory_system):
    """Enhanced document upload with performance optimization"""
    st.sidebar.header("📄 Document Upload")
    
    uploaded_file = st.sidebar.file_uploader(
        "Upload a document",
        type=['pdf', 'txt', 'docx', 'csv'],
        help="Upload documents for enhanced knowledge access"
    )
    
    if uploaded_file is not None:
        # Show file information and processing estimate
        try:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            estimated_chunks = uploaded_file.size // 1000  # Rough estimate
            time_estimate = estimate_processing_time(estimated_chunks)
            
            st.sidebar.info(f"""
            **File**: {uploaded_file.name}
            **Size**: {file_size_mb:.1f} MB
            **Estimated time**: {time_estimate}
            """)
            
        except Exception:
            pass
        
        if st.sidebar.button("Process Document", type="primary"):
            try:
                # Extract content chunks
                processor = DocumentProcessor()
                chunks = processor.process_file(uploaded_file, user_id)
                
                if chunks:
                    # Use optimized processing with progress tracking
                    doc_processor = OptimizedDocumentProcessor()
                    doc_id = doc_processor.store_document_optimized(
                        user_id, uploaded_file.name, chunks
                    )
                    
                    if doc_id:
                        st.sidebar.success(f"Document processed successfully")
                        st.rerun()
                    else:
                        st.sidebar.error("Processing failed")
                    
                    doc_processor.close()
                else:
                    st.sidebar.error("Could not extract content from file")
                    
            except Exception as e:
                st.sidebar.error(f"Processing error: {str(e)}")

def optimized_document_library_interface(user_id: str, memory_system):
    """Enhanced document library with processing status"""
    st.header("📚 Document Library")
    
    try:
        from integrated_memory import IntegratedMemorySystem
        
        # Get user documents via direct database query
        with memory_system.driver.session() as session:
            result = session.run("""
            MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)
            OPTIONAL MATCH (d)-[:CONTAINS_CHUNK]->(c:DocumentChunk)
            RETURN d.filename as filename, 
                   d.upload_timestamp as uploaded,
                   d.processing_status as status,
                   d.chunk_count as expected_chunks,
                   count(c) as stored_chunks
            ORDER BY d.upload_timestamp DESC
            """, user_id=user_id)
            
            documents = list(result)
        
        if documents:
            for doc in documents:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"📄 **{doc['filename']}**")
                
                with col2:
                    status = doc['status'] or 'complete'
                    if status == 'complete':
                        st.success("Ready")
                    elif status == 'processing':
                        st.warning("Processing")
                    else:
                        st.error("Failed")
                
                with col3:
                    chunks_text = f"{doc['stored_chunks']}"
                    if doc['expected_chunks'] and doc['expected_chunks'] != doc['stored_chunks']:
                        chunks_text += f"/{doc['expected_chunks']}"
                    st.write(f"{chunks_text} chunks")
                
                with col4:
                    if st.button("🗑️", key=f"delete_{doc['filename']}", help="Delete document"):
                        delete_document(user_id, doc['filename'], memory_system)
                        st.rerun()
                
                st.divider()
        else:
            st.info("No documents uploaded yet. Use the sidebar to upload your first document.")
            
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")

def delete_document(user_id: str, filename: str, memory_system):
    """Delete a document and all its chunks"""
    try:
        with memory_system.driver.session() as session:
            result = session.run("""
            MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document {filename: $filename})
            OPTIONAL MATCH (d)-[:CONTAINS_CHUNK]->(c:DocumentChunk)
            DETACH DELETE d, c
            RETURN count(d) as deleted
            """, user_id=user_id, filename=filename)
            
            deleted = result.single()['deleted']
            if deleted > 0:
                st.success(f"Deleted {filename}")
            else:
                st.error("Document not found")
                
    except Exception as e:
        st.error(f"Delete failed: {str(e)}")

def cleanup_processing_failures(user_id: str, memory_system):
    """Clean up any stuck or failed document processing"""
    try:
        processor = OptimizedDocumentProcessor()
        cleaned = processor.cleanup_failed_uploads(user_id)
        processor.close()
        
        if cleaned > 0:
            st.info(f"Cleaned up {cleaned} incomplete uploads")
            
    except Exception as e:
        st.error(f"Cleanup failed: {str(e)}")