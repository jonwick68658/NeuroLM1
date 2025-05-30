#!/usr/bin/env python3

import os
from neo4j import GraphDatabase
import logging

def setup_vector_indexes():
    """Create vector indexes for memory and document systems"""
    
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    
    with driver.session() as session:
        try:
            # Check if memory vector index exists
            result = session.run("SHOW INDEXES YIELD name WHERE name = 'memory_embeddings'")
            if not list(result):
                print("Creating memory vector index...")
                session.run("""
                CREATE VECTOR INDEX memory_embeddings FOR (m:Memory) ON (m.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
                """)
                print("Memory vector index created successfully")
            else:
                print("Memory vector index already exists")
                
            # Check if document vector index exists
            result = session.run("SHOW INDEXES YIELD name WHERE name = 'document_embeddings'")
            if not list(result):
                print("Creating document vector index...")
                session.run("""
                CREATE VECTOR INDEX document_embeddings FOR (d:DocumentChunk) ON (d.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
                """)
                print("Document vector index created successfully")
            else:
                print("Document vector index already exists")
                
            # Create constraint for memory IDs if not exists
            try:
                session.run("CREATE CONSTRAINT memory_id_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE")
                print("Memory ID constraint ensured")
            except Exception:
                pass
                
            # Create constraint for document chunk IDs if not exists
            try:
                session.run("CREATE CONSTRAINT doc_chunk_id_unique IF NOT EXISTS FOR (d:DocumentChunk) REQUIRE d.id IS UNIQUE")
                print("Document chunk ID constraint ensured")
            except Exception:
                pass
                
            # Create constraint for user IDs if not exists
            try:
                session.run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
                print("User ID constraint ensured")
            except Exception:
                pass
                
            print("Vector infrastructure setup complete")
            
        except Exception as e:
            print(f"Error setting up vector infrastructure: {e}")
            
    driver.close()

if __name__ == "__main__":
    setup_vector_indexes()