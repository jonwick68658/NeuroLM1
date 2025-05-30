#!/usr/bin/env python3
"""
Optimized Document Processing Pipeline
Fixes slow uploads with batch processing and parallel embedding generation
"""

import os
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from neo4j import GraphDatabase
from utils import generate_embedding
import uuid
import time
from typing import List, Dict, Any
import streamlit as st

class OptimizedDocumentProcessor:
    """Enhanced document processor with batch operations and progress tracking"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
        self.batch_size = 10  # Process embeddings in batches
        self.max_workers = 5  # Parallel embedding generation
    
    def store_document_optimized(self, user_id: str, filename: str, content_chunks: List[str]) -> str:
        """Store document with optimized batch processing and progress tracking"""
        
        if not content_chunks:
            return None
            
        doc_id = str(uuid.uuid4())
        total_chunks = len(content_chunks)
        
        # Create progress tracking
        progress_bar = st.progress(0, text=f"Processing {filename}...")
        status_text = st.empty()
        
        try:
            # Step 1: Create document record immediately
            with self.driver.session() as session:
                session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (d:Document {
                    id: $doc_id,
                    user_id: $user_id,
                    filename: $filename,
                    upload_timestamp: datetime(),
                    chunk_count: $chunk_count,
                    processing_status: 'processing'
                })
                CREATE (u)-[:UPLOADED]->(d)
                """, 
                user_id=user_id, 
                doc_id=doc_id, 
                filename=filename, 
                chunk_count=total_chunks
                )
            
            status_text.text(f"Created document record for {total_chunks} chunks")
            progress_bar.progress(0.1, text="Document record created...")
            
            # Step 2: Process chunks in batches with parallel embedding generation
            processed_count = 0
            
            for batch_start in range(0, total_chunks, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total_chunks)
                batch_chunks = content_chunks[batch_start:batch_end]
                
                # Generate embeddings in parallel for this batch
                embeddings = self._generate_embeddings_parallel(batch_chunks)
                
                # Store batch to database
                self._store_chunk_batch(doc_id, user_id, filename, batch_chunks, embeddings, batch_start)
                
                processed_count += len(batch_chunks)
                progress = 0.1 + (processed_count / total_chunks) * 0.9
                
                progress_bar.progress(progress, text=f"Processed {processed_count}/{total_chunks} chunks...")
                status_text.text(f"Batch {batch_start//self.batch_size + 1}/{(total_chunks + self.batch_size - 1)//self.batch_size} complete")
            
            # Step 3: Mark document as complete
            with self.driver.session() as session:
                session.run("""
                MATCH (d:Document {id: $doc_id})
                SET d.processing_status = 'complete',
                    d.completion_timestamp = datetime()
                """, doc_id=doc_id)
            
            progress_bar.progress(1.0, text=f"✅ {filename} processed successfully!")
            status_text.text(f"Document processing complete: {total_chunks} chunks stored")
            
            # Clear progress indicators after a moment
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
            return doc_id
            
        except Exception as e:
            # Mark document as failed
            try:
                with self.driver.session() as session:
                    session.run("""
                    MATCH (d:Document {id: $doc_id})
                    SET d.processing_status = 'failed',
                        d.error_message = $error
                    """, doc_id=doc_id, error=str(e))
            except:
                pass
            
            progress_bar.empty()
            status_text.empty()
            st.error(f"Document processing failed: {str(e)}")
            return None
    
    def _generate_embeddings_parallel(self, chunks: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple chunks in parallel"""
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all embedding tasks
            future_to_chunk = {
                executor.submit(generate_embedding, chunk): i 
                for i, chunk in enumerate(chunks)
            }
            
            # Collect results in order
            embeddings = [None] * len(chunks)
            for future in future_to_chunk:
                try:
                    chunk_index = future_to_chunk[future]
                    embedding = future.result(timeout=30)  # 30 second timeout per embedding
                    embeddings[chunk_index] = embedding
                except Exception as e:
                    print(f"Embedding generation failed for chunk {future_to_chunk[future]}: {e}")
                    # Use a zero vector as fallback
                    embeddings[future_to_chunk[future]] = [0.0] * 1536
            
            return embeddings
    
    def _store_chunk_batch(self, doc_id: str, user_id: str, filename: str, 
                          chunks: List[str], embeddings: List[List[float]], start_index: int):
        """Store a batch of chunks to the database efficiently"""
        
        with self.driver.session() as session:
            # Use a single transaction for the entire batch
            with session.begin_transaction() as tx:
                for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_id = str(uuid.uuid4())
                    chunk_index = start_index + i
                    
                    tx.run("""
                    MATCH (d:Document {id: $doc_id})
                    CREATE (c:DocumentChunk {
                        id: $chunk_id,
                        user_id: $user_id,
                        doc_id: $doc_id,
                        filename: $filename,
                        chunk_index: $chunk_index,
                        content: $chunk_content,
                        embedding: $embedding,
                        created_at: datetime()
                    })
                    CREATE (d)-[:CONTAINS_CHUNK]->(c)
                    """, 
                    doc_id=doc_id,
                    chunk_id=chunk_id,
                    user_id=user_id,
                    filename=filename,
                    chunk_index=chunk_index,
                    chunk_content=chunk_content,
                    embedding=embedding
                    )
    
    def get_processing_status(self, doc_id: str) -> Dict[str, Any]:
        """Get document processing status"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (d:Document {id: $doc_id})
                OPTIONAL MATCH (d)-[:CONTAINS_CHUNK]->(c:DocumentChunk)
                RETURN d.filename as filename,
                       d.processing_status as status,
                       d.chunk_count as expected_chunks,
                       count(c) as stored_chunks,
                       d.error_message as error
                """, doc_id=doc_id)
                
                record = result.single()
                if record:
                    return {
                        'filename': record['filename'],
                        'status': record['status'],
                        'expected_chunks': record['expected_chunks'],
                        'stored_chunks': record['stored_chunks'],
                        'error': record['error']
                    }
                else:
                    return {'status': 'not_found'}
                    
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def cleanup_failed_uploads(self, user_id: str):
        """Clean up any failed or incomplete document uploads"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)
                WHERE d.processing_status IN ['processing', 'failed'] 
                   OR d.processing_status IS NULL
                OPTIONAL MATCH (d)-[:CONTAINS_CHUNK]->(c:DocumentChunk)
                DETACH DELETE d, c
                RETURN count(DISTINCT d) as cleaned_docs
                """, user_id=user_id)
                
                record = result.single()
                return record['cleaned_docs'] if record else 0
                
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return 0
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()

# Performance comparison function
def estimate_processing_time(chunk_count: int) -> str:
    """Estimate processing time for document"""
    if chunk_count < 50:
        return "< 30 seconds"
    elif chunk_count < 200:
        return "1-2 minutes" 
    elif chunk_count < 500:
        return "2-4 minutes"
    else:
        return f"4-8 minutes (large document with {chunk_count} chunks)"

if __name__ == "__main__":
    # Test the optimized processor
    processor = OptimizedDocumentProcessor()
    
    # Example usage
    test_chunks = [f"This is test chunk {i} with some content to process." for i in range(20)]
    
    print("Testing optimized document processor...")
    start_time = time.time()
    
    doc_id = processor.store_document_optimized("test_user", "test_optimized.pdf", test_chunks)
    
    end_time = time.time()
    print(f"Processing time: {end_time - start_time:.2f} seconds")
    print(f"Document ID: {doc_id}")
    
    processor.close()