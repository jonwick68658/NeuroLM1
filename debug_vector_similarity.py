#!/usr/bin/env python3
"""
Debug Vector Similarity Issues
Investigate the actual format of embeddings being stored and retrieved
"""

import os
from dotenv import load_dotenv
from neural_memory import NeuralMemorySystem
from utils import generate_embedding
import json

def debug_embeddings():
    """Debug embedding format and Neo4j vector compatibility"""
    load_dotenv()
    
    print("=== Vector Similarity Debug ===")
    
    try:
        # Initialize memory system
        memory = NeuralMemorySystem()
        
        # Test embedding generation
        print("\n1. Testing embedding generation...")
        test_text = "Hello world"
        embedding = generate_embedding(test_text)
        
        print(f"Embedding type: {type(embedding)}")
        print(f"Embedding length: {len(embedding) if embedding else 'None'}")
        print(f"First 5 values: {embedding[:5] if embedding else 'None'}")
        print(f"All values are numbers: {all(isinstance(x, (int, float)) for x in embedding) if embedding else 'None'}")
        
        # Check actual stored embeddings
        print("\n2. Checking stored embeddings in database...")
        
        with memory.driver.session() as session:
            # Check memory embeddings
            result = session.run("""
            MATCH (m:Memory)
            WHERE m.embedding IS NOT NULL
            RETURN m.id, m.embedding, size(m.embedding) as embedding_size
            LIMIT 3
            """)
            
            print("Memory embeddings:")
            for record in result:
                embedding_data = record['m.embedding']
                print(f"  Memory ID: {record['m.id']}")
                print(f"  Size: {record['embedding_size']}")
                print(f"  Type: {type(embedding_data)}")
                print(f"  First few values: {embedding_data[:3] if embedding_data else 'None'}")
                
                # Test if this embedding works with vector similarity
                try:
                    test_result = session.run("""
                    MATCH (m:Memory {id: $memory_id})
                    WHERE m.embedding IS NOT NULL
                    WITH m, vector.similarity.cosine(m.embedding, $test_embedding) as similarity
                    RETURN similarity
                    """, memory_id=record['m.id'], test_embedding=embedding)
                    
                    similarity_record = test_result.single()
                    if similarity_record:
                        print(f"  Vector similarity test: SUCCESS ({similarity_record['similarity']})")
                    else:
                        print(f"  Vector similarity test: NO RESULT")
                        
                except Exception as e:
                    print(f"  Vector similarity test: FAILED - {e}")
                
                print()
            
            # Check topic embeddings
            print("Topic embeddings:")
            topic_result = session.run("""
            MATCH (t:Topic)
            WHERE t.embedding IS NOT NULL
            RETURN t.id, t.name, t.embedding, size(t.embedding) as embedding_size
            LIMIT 3
            """)
            
            for record in topic_result:
                embedding_data = record['t.embedding']
                print(f"  Topic: {record['t.name']}")
                print(f"  Size: {record['embedding_size']}")
                print(f"  Type: {type(embedding_data)}")
                
                # Test vector similarity on topics
                try:
                    test_result = session.run("""
                    MATCH (t:Topic {id: $topic_id})
                    WHERE t.embedding IS NOT NULL
                    WITH t, vector.similarity.cosine(t.embedding, $test_embedding) as similarity
                    RETURN similarity
                    """, topic_id=record['t.id'], test_embedding=embedding)
                    
                    similarity_record = test_result.single()
                    if similarity_record:
                        print(f"  Vector similarity test: SUCCESS ({similarity_record['similarity']})")
                    else:
                        print(f"  Vector similarity test: NO RESULT")
                        
                except Exception as e:
                    print(f"  Vector similarity test: FAILED - {e}")
                
                print()
        
        # Check vector indexes
        print("3. Checking vector indexes...")
        with memory.driver.session() as session:
            index_result = session.run("SHOW INDEXES")
            
            for record in index_result:
                if 'vector' in str(record).lower():
                    print(f"  Found vector index: {record}")
        
        memory.close()
        
    except Exception as e:
        print(f"Debug failed: {e}")

if __name__ == "__main__":
    debug_embeddings()