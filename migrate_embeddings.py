#!/usr/bin/env python3

import os
from neo4j import GraphDatabase
from utils import generate_embedding
import logging

def migrate_document_embeddings():
    """Add embeddings to existing document chunks that don't have them"""
    
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    
    with driver.session() as session:
        # Find all document chunks to regenerate embeddings with OpenAI
        result = session.run("""
        MATCH (c:DocumentChunk)
        RETURN c.id AS chunk_id, c.content AS content
        """)
        
        chunks_to_update = list(result)
        print(f"Found {len(chunks_to_update)} document chunks to regenerate with OpenAI embeddings")
        
        if not chunks_to_update:
            print("All document chunks already have embeddings")
            return
        
        # Update chunks with embeddings
        updated_count = 0
        failed_count = 0
        
        for chunk in chunks_to_update:
            try:
                content = chunk['content']
                chunk_id = chunk['chunk_id']
                
                if content and content.strip():
                    embedding = generate_embedding(content)
                    
                    # Only update if we got a valid embedding
                    if embedding and not all(x == 0.0 for x in embedding):
                        session.run("""
                        MATCH (c:DocumentChunk {id: $chunk_id})
                        SET c.embedding = $embedding
                        """, chunk_id=chunk_id, embedding=embedding)
                        updated_count += 1
                        print(f"Updated chunk {chunk_id[:8]}... with embedding")
                    else:
                        failed_count += 1
                        print(f"Failed to generate embedding for chunk {chunk_id[:8]}...")
                else:
                    failed_count += 1
                    print(f"Skipped empty chunk {chunk_id[:8]}...")
                    
            except Exception as e:
                failed_count += 1
                print(f"Error processing chunk {chunk_id[:8]}...: {e}")
        
        print(f"Migration complete: {updated_count} updated, {failed_count} failed")

def migrate_memory_embeddings():
    """Add embeddings to existing memories that don't have them"""
    
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    
    with driver.session() as session:
        # Find memories without embeddings
        result = session.run("""
        MATCH (m:Memory)
        WHERE m.embedding IS NULL
        RETURN m.id AS memory_id, m.content AS content
        """)
        
        memories_to_update = list(result)
        print(f"Found {len(memories_to_update)} memories without embeddings")
        
        if not memories_to_update:
            print("All memories already have embeddings")
            return
        
        # Update memories with embeddings
        updated_count = 0
        failed_count = 0
        
        for memory in memories_to_update:
            try:
                content = memory['content']
                memory_id = memory['memory_id']
                
                if content and content.strip():
                    embedding = generate_embedding(content)
                    
                    # Only update if we got a valid embedding
                    if embedding and not all(x == 0.0 for x in embedding):
                        session.run("""
                        MATCH (m:Memory {id: $memory_id})
                        SET m.embedding = $embedding
                        """, memory_id=memory_id, embedding=embedding)
                        updated_count += 1
                        print(f"Updated memory {memory_id[:8]}... with embedding")
                    else:
                        failed_count += 1
                        print(f"Failed to generate embedding for memory {memory_id[:8]}...")
                else:
                    failed_count += 1
                    print(f"Skipped empty memory {memory_id[:8]}...")
                    
            except Exception as e:
                failed_count += 1
                print(f"Error processing memory {memory_id[:8]}...: {e}")
        
        print(f"Memory migration complete: {updated_count} updated, {failed_count} failed")

if __name__ == "__main__":
    print("=== MIGRATING DOCUMENT EMBEDDINGS ===")
    migrate_document_embeddings()
    
    print("\n=== MIGRATING MEMORY EMBEDDINGS ===")
    migrate_memory_embeddings()
    
    print("\nEmbedding migration complete!")