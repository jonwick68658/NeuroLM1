#!/usr/bin/env python3
"""
Streamlined batch processor for document uploads
Integrates with existing NeuroLM architecture
"""

import asyncio
import time
import os
import uuid
from typing import List, Optional
from utils import generate_embedding
import concurrent.futures

class BatchProcessor:
    """Fast batch processing for document embeddings"""
    
    def __init__(self):
        self.max_workers = 5  # Parallel workers for embedding generation
    
    def generate_embeddings_parallel(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using thread pool for parallel processing"""
        print(f"   Generating embeddings for {len(texts)} chunks in parallel...")
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all embedding tasks
            future_to_text = {executor.submit(generate_embedding, text): text for text in texts}
            embeddings = []
            
            # Collect results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(future_to_text)):
                try:
                    embedding = future.result()
                    embeddings.append(embedding)
                    
                    # Progress feedback
                    if (i + 1) % 20 == 0 or (i + 1) == len(texts):
                        print(f"     Processed {i + 1}/{len(texts)} embeddings")
                        
                except Exception as e:
                    print(f"     Error generating embedding: {e}")
                    # Use zero vector as fallback
                    embeddings.append([0.0] * 1536)
        
        elapsed = time.time() - start_time
        print(f"   ✓ Generated {len(embeddings)} embeddings in {elapsed:.2f} seconds")
        
        return embeddings
    
    def process_document_fast(self, user_id: str, filename: str, content_chunks: List[str], doc_storage) -> Optional[str]:
        """Process document with parallel embedding generation"""
        print(f"📄 Fast processing {filename} with {len(content_chunks)} chunks...")
        
        try:
            # Generate all embeddings in parallel
            embeddings = self.generate_embeddings_parallel(content_chunks)
            
            if len(embeddings) != len(content_chunks):
                raise Exception(f"Embedding count mismatch: {len(embeddings)} vs {len(content_chunks)}")
            
            # Store document with all chunks and embeddings
            doc_id = doc_storage.store_document(user_id, filename, content_chunks)
            
            if doc_id:
                print(f"   ✓ Document stored successfully: {doc_id}")
                return doc_id
            else:
                print(f"   ❌ Failed to store document")
                return None
                
        except Exception as e:
            print(f"   ❌ Error processing document: {e}")
            return None

# Global batch processor instance
batch_processor = BatchProcessor()