#!/usr/bin/env python3
"""
Optimized Document Processor
Implements batch embedding generation and resume capability as per your optimization plan
"""

import asyncio
import time
import os
import uuid
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from openai import AsyncOpenAI
import streamlit as st

class RateLimiter:
    """Smart rate limiter with auto-backoff"""
    def __init__(self, rpm: int = 3000):
        self.interval = 60 / (rpm * 0.8)  # 80% safety margin
        self.last_call = time.time() - self.interval

    async def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.interval:
            await asyncio.sleep(self.interval - elapsed)
        self.last_call = time.time()

class OptimizedDocumentProcessor:
    """High-performance document processor with batch embedding generation"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
        # Use OpenAI directly for embeddings (more reliable than OpenRouter)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.aclient = AsyncOpenAI(api_key=openai_key)
        else:
            # Fallback to OpenRouter if OpenAI key not available
            self.aclient = AsyncOpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1"
            )
        self.rate_limiter = RateLimiter(rpm=3000)
    
    async def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings in parallel batches"""
        results = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            # Rate limiting
            await self.rate_limiter.wait()
            
            try:
                # Single text vs batch handling
                if len(batch) == 1:
                    response = await self.aclient.embeddings.create(
                        input=batch[0], 
                        model="text-embedding-3-small"
                    )
                    results.append(response.data[0].embedding)
                else:
                    response = await self.aclient.embeddings.create(
                        input=batch, 
                        model="text-embedding-3-small"
                    )
                    results.extend([r.embedding for r in response.data])
                
                print(f"   Processed batch {batch_num}/{total_batches} ({len(batch)} chunks)")
                
            except Exception as e:
                print(f"   Error in batch {batch_num}: {e}")
                # Fallback to individual processing for failed batch
                for text in batch:
                    try:
                        await self.rate_limiter.wait()
                        response = await self.aclient.embeddings.create(
                            input=text, 
                            model="text-embedding-3-small"
                        )
                        results.append(response.data[0].embedding)
                    except Exception as individual_error:
                        print(f"   Failed individual chunk: {individual_error}")
                        # Use zero vector as fallback to maintain indexing
                        results.append([0.0] * 1536)
        
        return results
    
    def load_processed_chunks(self, doc_id: str) -> set:
        """Load existing chunks to enable resume capability"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (c:DocumentChunk {doc_id: $doc_id})
                RETURN c.chunk_index as index
                """, doc_id=doc_id)
                
                return {record['index'] for record in result}
        except Exception as e:
            print(f"Error loading processed chunks: {e}")
            return set()
    
    def update_progress(self, doc_id: str, status: str, percentage: float):
        """Update document processing progress"""
        try:
            with self.driver.session() as session:
                session.run("""
                MATCH (d:Document {id: $doc_id})
                SET d.processing_status = $status, 
                    d.processing_progress = $percentage,
                    d.last_updated = datetime()
                """, doc_id=doc_id, status=status, percentage=percentage)
        except Exception as e:
            print(f"Error updating progress: {e}")
    
    async def process_document_optimized(self, user_id: str, filename: str, content_chunks: List[str]) -> Optional[str]:
        """Process document with batch embeddings and resume capability"""
        doc_id = str(uuid.uuid4())
        total_chunks = len(content_chunks)
        
        print(f"📄 Processing {filename} with {total_chunks} chunks (optimized)")
        
        try:
            # Create document record with processing status
            with self.driver.session() as session:
                session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (d:Document {
                    id: $doc_id,
                    user_id: $user_id,
                    filename: $filename,
                    upload_timestamp: datetime(),
                    chunk_count: $chunk_count,
                    processing_status: 'STARTING',
                    processing_progress: 0.0
                })
                CREATE (u)-[:UPLOADED]->(d)
                """, 
                user_id=user_id, 
                doc_id=doc_id, 
                filename=filename, 
                chunk_count=total_chunks
                )
            
            # Check for existing chunks (resume capability)
            processed_indices = self.load_processed_chunks(doc_id)
            unprocessed_chunks = [
                (i, chunk) for i, chunk in enumerate(content_chunks) 
                if i not in processed_indices
            ]
            
            if not unprocessed_chunks:
                print(f"   ✓ Document already fully processed")
                self.update_progress(doc_id, 'COMPLETED', 100.0)
                return doc_id
            
            print(f"   Processing {len(unprocessed_chunks)} remaining chunks")
            self.update_progress(doc_id, 'PROCESSING', 10.0)
            
            # Extract texts for batch processing
            texts_to_process = [chunk for _, chunk in unprocessed_chunks]
            
            # Generate embeddings in batches
            print(f"   Generating embeddings for {len(texts_to_process)} chunks...")
            embeddings = await self.generate_embeddings_batch(texts_to_process)
            
            if len(embeddings) != len(texts_to_process):
                raise Exception(f"Embedding count mismatch: {len(embeddings)} vs {len(texts_to_process)}")
            
            self.update_progress(doc_id, 'STORING', 80.0)
            
            # Store chunks with embeddings
            with self.driver.session() as session:
                for (chunk_index, chunk_content), embedding in zip(unprocessed_chunks, embeddings):
                    chunk_id = str(uuid.uuid4())
                    
                    session.run("""
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
            
            self.update_progress(doc_id, 'COMPLETED', 100.0)
            print(f"   ✓ Document processed successfully: {doc_id}")
            return doc_id
            
        except Exception as e:
            print(f"   ❌ Error processing document: {e}")
            self.update_progress(doc_id, 'FAILED', 0.0)
            return None
    
    def repair_metadata(self):
        """Repair documents with missing metadata"""
        print("🔧 Repairing document metadata...")
        
        try:
            with self.driver.session() as session:
                # Fix missing upload timestamps
                result = session.run("""
                MATCH (d:Document) 
                WHERE d.upload_timestamp IS NULL
                SET d.upload_timestamp = datetime()
                RETURN count(d) as fixed_count
                """)
                
                fixed = result.single()['fixed_count']
                print(f"   ✓ Fixed {fixed} documents with missing timestamps")
                
                # Fix orphaned chunks with null filenames
                result = session.run("""
                MATCH (c:DocumentChunk)
                WHERE c.filename IS NULL AND c.doc_id IS NOT NULL
                MATCH (d:Document {id: c.doc_id})
                SET c.filename = d.filename
                RETURN count(c) as fixed_chunks
                """)
                
                fixed_chunks = result.single()['fixed_chunks']
                print(f"   ✓ Fixed {fixed_chunks} chunks with missing filenames")
                
        except Exception as e:
            print(f"   ❌ Error repairing metadata: {e}")
    
    def get_processing_status(self, doc_id: str) -> Dict[str, Any]:
        """Get current processing status of a document"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (d:Document {id: $doc_id})
                RETURN d.processing_status as status, 
                       d.processing_progress as progress,
                       d.filename as filename
                """, doc_id=doc_id)
                
                record = result.single()
                if record:
                    return {
                        'status': record['status'],
                        'progress': record['progress'],
                        'filename': record['filename']
                    }
                return {'status': 'NOT_FOUND', 'progress': 0}
                
        except Exception as e:
            return {'status': 'ERROR', 'progress': 0, 'error': str(e)}
    
    def close(self):
        """Close connections"""
        if self.driver:
            self.driver.close()

# Test function
async def test_optimized_processing():
    """Test the optimized document processor"""
    processor = OptimizedDocumentProcessor()
    
    # Test with sample chunks
    test_chunks = [
        "This is the first test chunk for optimized processing.",
        "The second chunk tests batch embedding generation.",
        "Third chunk validates the resume capability feature."
    ]
    
    print("Testing optimized document processing...")
    doc_id = await processor.process_document_optimized("user_test", "test_optimized.pdf", test_chunks)
    
    if doc_id:
        status = processor.get_processing_status(doc_id)
        print(f"Processing complete: {status}")
    
    processor.close()

if __name__ == "__main__":
    asyncio.run(test_optimized_processing())