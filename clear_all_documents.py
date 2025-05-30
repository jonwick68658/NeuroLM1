#!/usr/bin/env python3
"""
Clear all documents and document chunks from Neo4j database
"""

import os
from neo4j import GraphDatabase

def clear_all_documents():
    """Delete all documents, chunks, and knowledge from Neo4j"""
    try:
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session() as session:
            print("🗑️ Deleting all documents and document chunks...")
            
            # Delete all DocumentChunk nodes and relationships
            result = session.run("""
            MATCH (c:DocumentChunk) 
            DETACH DELETE c
            RETURN count(*) as deleted_chunks
            """)
            deleted_chunks = result.single()['deleted_chunks']
            print(f"   ✓ Deleted {deleted_chunks} document chunks")
            
            # Delete all Document nodes and relationships
            result = session.run("""
            MATCH (d:Document) 
            DETACH DELETE d
            RETURN count(*) as deleted_docs
            """)
            deleted_docs = result.single()['deleted_docs']
            print(f"   ✓ Deleted {deleted_docs} documents")
            
            # Delete all Knowledge nodes (legacy document data)
            result = session.run("""
            MATCH (k:Knowledge) 
            DETACH DELETE k
            RETURN count(*) as deleted_knowledge
            """)
            deleted_knowledge = result.single()['deleted_knowledge']
            print(f"   ✓ Deleted {deleted_knowledge} knowledge entries")
            
            # Delete any orphaned relationships related to documents
            result = session.run("""
            MATCH ()-[r:CONTAINS_CHUNK|UPLOADED]->()
            WHERE NOT exists(r)
            DELETE r
            RETURN count(*) as deleted_rels
            """)
            
            print("🧹 Database cleanup complete - all document data removed")
            
        driver.close()
        
    except Exception as e:
        print(f"❌ Error clearing documents: {e}")

if __name__ == "__main__":
    clear_all_documents()