#!/usr/bin/env python3
"""
Debug Live Vector Issues
Compare working embeddings vs failing ones in real-time
"""

import os
from dotenv import load_dotenv
from neural_memory import NeuralMemorySystem
from utils import generate_embedding

def debug_live_vectors():
    """Debug vector similarity in live context"""
    load_dotenv()
    
    print("=== Live Vector Debug ===")
    
    try:
        memory = NeuralMemorySystem()
        
        # Test current user's data
        test_user = "test_user_123"
        
        with memory.driver.session() as session:
            # Get recent memories that are failing
            recent_result = session.run("""
            MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
            WHERE m.created_at > datetime() - duration('PT1H')
            RETURN m.id, m.content, m.embedding, t.name as topic
            ORDER BY m.created_at DESC
            LIMIT 3
            """, user_id=test_user)
            
            print("Recent memories from last hour:")
            for record in recent_result:
                memory_id = record['m.id']
                content = record['m.content'][:50] + "..."
                embedding = record['m.embedding']
                topic = record['topic']
                
                print(f"Memory: {content}")
                print(f"Topic: {topic}")
                print(f"Embedding type: {type(embedding)}")
                print(f"Embedding length: {len(embedding) if embedding else 'None'}")
                
                if embedding:
                    # Test vector similarity with this exact embedding
                    try:
                        test_embedding = generate_embedding("test query")
                        
                        similarity_result = session.run("""
                        WITH $memory_embedding as mem_emb, $test_embedding as test_emb
                        RETURN vector.similarity.cosine(mem_emb, test_emb) as similarity
                        """, memory_embedding=embedding, test_embedding=test_embedding)
                        
                        sim_record = similarity_result.single()
                        if sim_record:
                            print(f"Direct similarity test: SUCCESS ({sim_record['similarity']})")
                        else:
                            print("Direct similarity test: NO RESULT")
                            
                    except Exception as e:
                        print(f"Direct similarity test: FAILED - {e}")
                        
                        # Check if it's the embedding parameter format
                        print(f"Memory embedding sample: {embedding[:3] if len(embedding) > 3 else embedding}")
                        print(f"Test embedding sample: {test_embedding[:3] if len(test_embedding) > 3 else test_embedding}")
                
                print("-" * 50)
        
        memory.close()
        
    except Exception as e:
        print(f"Debug failed: {e}")

if __name__ == "__main__":
    debug_live_vectors()