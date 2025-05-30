#!/usr/bin/env python3

import os
from neo4j import GraphDatabase
from document_storage import DocumentStorage

def check_document_storage():
    """Debug the document storage to see what's actually stored"""
    
    # Initialize Neo4j connection
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    
    doc_storage = DocumentStorage(driver)
    
    with driver.session() as session:
        # Check documents
        print("=== DOCUMENTS ===")
        docs = session.run("MATCH (d:Document) RETURN d.filename, d.user_id, d.id, d.created_at")
        for doc in docs:
            print(f"Document: {doc['d.filename']} (ID: {doc['d.id']}, User: {doc['d.user_id']})")
        
        print("\n=== DOCUMENT CHUNKS ===")
        chunks = session.run("""
        MATCH (c:DocumentChunk)-[:BELONGS_TO]->(d:Document) 
        RETURN d.filename, c.chunk_index, substring(c.content, 0, 200) as content_preview
        ORDER BY d.filename, c.chunk_index
        LIMIT 10
        """)
        
        for chunk in chunks:
            print(f"Chunk {chunk['c.chunk_index']} from {chunk['d.filename']}:")
            print(f"  Content: {chunk['content_preview']}...")
            print()
        
        print("\n=== SEARCH TEST ===")
        # Test search functionality
        test_queries = ["title", "document", "implementation", "processing"]
        
        for query in test_queries:
            print(f"Searching for: '{query}'")
            results = doc_storage.search_documents("default_user", query, limit=3)
            print(f"  Found {len(results)} results")
            for i, result in enumerate(results):
                print(f"    {i+1}. {result['filename']} (similarity: {result['similarity']})")
                print(f"       Preview: {result['chunk_content'][:100]}...")
            print()

if __name__ == "__main__":
    check_document_storage()