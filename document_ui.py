import streamlit as st
from file_processor import DocumentProcessor
from document_storage import DocumentStorage
from batch_processor import batch_processor
import os
import time
from typing import List, Dict, Any

def document_upload_section(user_id: str, memory_system):
    """Sidebar document upload widget"""
    st.sidebar.markdown("### 📄 Knowledge Upload")
    
    # File type explanations
    with st.sidebar.expander("Supported Formats"):
        st.caption("""
        - **PDF**: Text-based documents  
        - **DOCX**: Microsoft Word documents  
        - **CSV/Excel**: Tabular data  
        - **Text/Markdown**: Raw text files  
        """)
    
    # Initialize session state for upload tracking
    if "processed_files" not in st.session_state:
        st.session_state.processed_files = set()
    
    # File uploader
    uploaded_files = st.sidebar.file_uploader(
        "Upload documents",
        type=["pdf", "docx", "csv", "txt", "xlsx", "md"],
        accept_multiple_files=True,
        help="Documents are automatically processed when uploaded"
    )
    
    # Automatic processing on upload
    if uploaded_files:
        processor = DocumentProcessor()
        doc_storage = DocumentStorage(memory_system.driver)
        
        # Check for new files that haven't been processed
        new_files = []
        for file in uploaded_files:
            file_key = f"{file.name}_{file.size}_{user_id}"
            if file_key not in st.session_state.processed_files:
                new_files.append((file, file_key))
        
        if new_files:
            progress_bar = st.sidebar.progress(0)
            status_container = st.sidebar.container()
            
            # Check for duplicates in database before processing
            existing_docs = doc_storage.get_user_documents(user_id)
            existing_filenames = {doc['filename'] for doc in existing_docs}
            
            successful_uploads = 0
            
            for i, (file, file_key) in enumerate(new_files):
                try:
                    # Skip if document already exists
                    if file.name in existing_filenames:
                        with status_container:
                            st.warning(f"Document {file.name} already exists - skipped")
                        st.session_state.processed_files.add(file_key)
                        continue
                    
                    with status_container:
                        st.info(f"Processing {file.name}...")
                    
                    # Process file into chunks
                    chunks = processor.process_file(file, user_id)
                    
                    # Use fast batch processing for embedding generation
                    doc_id = batch_processor.process_document_fast(
                        user_id=user_id,
                        filename=file.name, 
                        content_chunks=chunks,
                        doc_storage=doc_storage
                    )
                    
                    # Check if processing was successful
                    if doc_id:
                        # Mark as processed
                        st.session_state.processed_files.add(file_key)
                        
                        with status_container:
                            st.success(f"Added {len(chunks)} chunks from {file.name}")
                        
                        successful_uploads += 1
                    else:
                        with status_container:
                            st.error(f"Failed to process {file.name}")
                    
                except Exception as e:
                    with status_container:
                        st.error(f"Failed to process {file.name}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(new_files))
            
            # Clear progress and show summary
            progress_bar.empty()
            status_container.empty()
            
            if successful_uploads > 0:
                st.sidebar.success(f"Successfully processed {successful_uploads} new documents")
                # Refresh to show new documents
                time.sleep(1)
                st.rerun()

def document_library_interface(user_id: str, memory_system):
    """Main panel document management interface"""
    st.markdown("## 📚 Knowledge Library")
    
    doc_storage = DocumentStorage(memory_system.driver)
    
    # Get document statistics
    stats = doc_storage.get_document_stats(user_id)
    
    # Display stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents", stats['total_documents'])
    with col2:
        st.metric("Knowledge Chunks", stats['total_chunks'])
    with col3:
        if stats['total_documents'] > 0:
            avg_chunks = stats['total_chunks'] / stats['total_documents']
            st.metric("Avg Chunks/Doc", f"{avg_chunks:.1f}")
        else:
            st.metric("Avg Chunks/Doc", "0")
    
    # Search functionality
    st.markdown("### 🔍 Search Knowledge")
    search_query = st.text_input(
        "Search through your documents",
        placeholder="Enter keywords to search your knowledge base..."
    )
    
    if search_query:
        search_results = doc_storage.search_documents(user_id, search_query, limit=10)
        
        if search_results:
            st.markdown(f"Found {len(search_results)} relevant chunks:")
            
            for result in search_results:
                with st.expander(f"📄 {result['filename']} (Chunk {result['chunk_index'] + 1})"):
                    st.markdown(f"**Relevance:** {result['similarity']:.2f}")
                    st.markdown("**Content:**")
                    st.write(result['chunk_content'][:500] + "..." if len(result['chunk_content']) > 500 else result['chunk_content'])
                    
                    # Option to use this chunk in conversation
                    if st.button("Use in Chat", key=f"use_{result['doc_id']}_{result['chunk_index']}"):
                        st.session_state.document_context = {
                            "source": f"{result['filename']} (Chunk {result['chunk_index'] + 1})",
                            "content": result['chunk_content']
                        }
                        st.success("Added to conversation context!")
        else:
            st.info("No matching content found in your documents.")
    
    # Document management
    st.markdown("### 📋 Document Management")
    
    documents = doc_storage.get_user_documents(user_id)
    
    if not documents:
        st.info("No documents uploaded yet. Use the sidebar to upload your first document.")
        return
    
    # Document list
    for doc in documents:
        with st.container():
            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
            
            with col1:
                st.markdown(f"**{doc['filename']}**")
            
            with col2:
                st.markdown(f"{doc['chunk_count']} chunks")
            
            with col3:
                created_date = doc['created_at'].strftime('%Y-%m-%d')
                st.markdown(created_date)
            
            with col4:
                if st.button("🗑️ Delete", key=f"delete_{doc['id']}"):
                    if doc_storage.delete_document(doc['id'], user_id):
                        st.success(f"Deleted {doc['filename']}")
                        st.rerun()
                    else:
                        st.error("Failed to delete document")
            
            # Preview toggle
            if st.toggle(f"Preview {doc['filename']}", key=f"preview_{doc['id']}"):
                preview_document(doc['id'], user_id, doc_storage)
            
            st.markdown("---")

def preview_document(doc_id: str, user_id: str, doc_storage: DocumentStorage):
    """Show document content with conversational integration"""
    chunks = doc_storage.get_document_chunks(doc_id, user_id)
    
    if not chunks:
        st.warning("No content found for this document.")
        return
    
    st.markdown("#### Document Content")
    
    for chunk in chunks:
        with st.expander(f"Chunk {chunk['chunk_index'] + 1}"):
            st.markdown(f"**Source:** {chunk['source']}")
            st.markdown("**Content:**")
            st.write(chunk['content'])
            
            # Context injection button
            if st.button(f"Use in Chat", key=f"use_chunk_{chunk['id']}"):
                st.session_state.document_context = {
                    "source": f"{chunk['source']} (Chunk {chunk['chunk_index'] + 1})",
                    "content": chunk['content']
                }
                st.success("Added to conversation context!")

def get_unified_context_for_chat(user_id: str, query: str, memory_system) -> str:
    """Get unified context combining both memory and document searches with debugging"""
    if not hasattr(memory_system, 'driver'):
        return ""
    
    try:
        context_parts = []
        
        # Get memory context with detailed error handling
        memory_context = []
        try:
            # For name queries, search specifically for name-providing conversations
            if any(word in query.lower() for word in ['name', 'who', 'ryan']):
                # Use direct database search to find name conversations
                from neo4j import GraphDatabase
                import os
                
                driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
                with driver.session() as session:
                    # Search for memories containing "Ryan" or "my name is"
                    result = session.run('''
                    MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                    WHERE toLower(m.content) CONTAINS "ryan" 
                       OR toLower(m.content) CONTAINS "my name is"
                       OR toLower(m.content) CONTAINS "name is"
                    RETURN m.content as content, m.timestamp as timestamp, m.role as role
                    ORDER BY m.timestamp ASC
                    ''', user_id=user_id)
                    
                    name_memories = list(result)
                    if name_memories:
                        memory_context = [mem['content'] for mem in name_memories]
                        context_parts.append("From your conversation history:")
                        for mem in name_memories:
                            context_parts.append(f"- {mem['role']}: {mem['content']}")
                    else:
                        # Fallback to recent conversation history
                        recent_memories = memory_system.get_conversation_history(user_id, limit=10)
                        if recent_memories:
                            memory_context = [mem.get('content', '') for mem in recent_memories if mem.get('content')]
                            context_parts.append("From your conversation history:")
                            for memory in memory_context[:5]:
                                context_parts.append(f"- {memory[:400]}")
                driver.close()
            else:
                # Use semantic search for other queries
                memory_results = memory_system.get_relevant_memories(query, user_id, limit=5)
                if memory_results:
                    memory_context = memory_results
                    context_parts.append("From your conversation history:")
                    for memory in memory_context[:3]:
                        context_parts.append(f"- {memory[:250]}...")
                        
        except Exception as e:
            # Log memory retrieval failure but continue
            context_parts.append(f"Memory search failed: {str(e)[:100]}")
        
        # Get document context with error handling
        document_results = []
        try:
            doc_storage = DocumentStorage(memory_system.driver)
            document_results = doc_storage.search_documents(user_id, query, limit=3)
            
            if document_results:
                context_parts.append("\nFrom your uploaded documents:")
                for result in document_results:
                    filename = result.get('filename', 'Unknown Document')
                    content = result.get('chunk_content', '')
                    similarity = result.get('similarity', 0)
                    context_parts.append(f"- From {filename} (relevance: {similarity:.2f}): {content[:300]}...")
        except Exception as e:
            context_parts.append(f"\nDocument search failed: {str(e)[:100]}")
        
        # If no results, provide debugging info
        if not memory_context and not document_results:
            try:
                # Get recent memories for debugging
                recent_memories = memory_system.get_conversation_history(user_id, limit=3)
                if recent_memories:
                    context_parts.append("\nRecent conversation (debug):")
                    for memory in recent_memories[:2]:
                        content = memory.get('content', '')[:150]
                        role = memory.get('role', 'unknown')
                        context_parts.append(f"- {role}: {content}...")
                
                # Get recent documents for debugging
                try:
                    doc_storage = DocumentStorage(memory_system.driver)
                    recent_docs = doc_storage._get_recent_document_chunks(user_id, limit=2)
                    if recent_docs:
                        context_parts.append("\nRecent documents (debug):")
                        for doc in recent_docs:
                            filename = doc.get('filename', 'Unknown')
                            content = doc.get('chunk_content', '')[:150]
                            context_parts.append(f"- From {filename}: {content}...")
                except Exception:
                    pass
                        
            except Exception as debug_e:
                context_parts.append(f"\nDebug search also failed: {str(debug_e)[:100]}")
        
        final_context = "\n".join(context_parts) if context_parts else ""
        
        # Add context quality indicator
        quality_indicator = f"\n\nContext quality: {len(memory_context)} memories, {len(document_results)} documents found"
        return final_context + quality_indicator
        
    except Exception as e:
        return f"Context retrieval completely failed: {str(e)[:200]}"


def get_document_context_for_chat(user_id: str, query: str, memory_system) -> str:
    """Get relevant document context for chat responses - DEPRECATED, use get_unified_context_for_chat"""
    return get_unified_context_for_chat(user_id, query, memory_system)

def display_document_stats_in_sidebar(user_id: str, memory_system):
    """Display document statistics in sidebar"""
    try:
        doc_storage = DocumentStorage(memory_system.driver)
        stats = doc_storage.get_document_stats(user_id)
        
        if stats['total_documents'] > 0:
            st.sidebar.markdown("---")
            st.sidebar.markdown("📊 **Knowledge Stats**")
            st.sidebar.caption(f"Documents: {stats['total_documents']}")
            st.sidebar.caption(f"Knowledge chunks: {stats['total_chunks']}")
    
    except Exception:
        # Silently fail if stats can't be retrieved
        pass