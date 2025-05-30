#!/usr/bin/env python3

import os
from neo4j import GraphDatabase
from document_storage import DocumentStorage
from utils import generate_embedding

def test_document_search():
    """Test the document search functionality"""
    
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    
    doc_storage = DocumentStorage(driver)
    
    # Test queries that should match content from the uploaded document
    test_queries = [
        "offers",
        "business",
        "marketing", 
        "sales",
        "acquisition",
        "Alex Hormozi",
        "100M"
    ]
    
    user_id = "user_Ryan"
    
    print("=== DOCUMENT SEARCH TEST ===")
    print(f"Testing search for user: {user_id}")
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = doc_storage.search_documents(user_id, query, limit=3)
        
        if results:
            print(f"  Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                similarity = result.get('similarity', 0)
                chunk_preview = result['chunk_content'][:150] + "..." if len(result['chunk_content']) > 150 else result['chunk_content']
                print(f"    {i}. {result['filename']} (similarity: {similarity:.3f})")
                print(f"       Preview: {chunk_preview}")
        else:
            print("  No results found")
    
    # Test embedding generation
    print("\n=== EMBEDDING TEST ===")
    test_text = "business acquisition and marketing offers"
    embedding = generate_embedding(test_text)
    print(f"Generated embedding for '{test_text}'")
    print(f"Embedding length: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
    print(f"All zeros? {all(x == 0.0 for x in embedding)}")
    
    driver.close()

if __name__ == "__main__":
    test_document_search()