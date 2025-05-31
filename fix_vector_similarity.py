#!/usr/bin/env python3
"""
Fix Vector Similarity Issue
Direct test and fix for Neo4j vector similarity errors
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from utils import generate_embedding

def fix_vector_similarity():
    """Fix the vector similarity compatibility issue"""
    load_dotenv()
    
    print("=== Fixing Vector Similarity ===")
    
    try:
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
        
        with driver.session() as session:
            # Test with actual stored embeddings
            print("Testing stored embeddings...")
            
            result = session.run("""
            MATCH (m:Memory)
            WHERE m.embedding IS NOT NULL
            RETURN m.id, m.embedding
            LIMIT 1
            """)
            
            record = result.single()
            if record:
                stored_embedding = record['m.embedding']
                memory_id = record['m.id']
                
                print(f"Testing memory {memory_id}")
                print(f"Stored embedding type: {type(stored_embedding)}")
                print(f"Stored embedding length: {len(stored_embedding)}")
                
                # Generate a test embedding
                test_embedding = generate_embedding("test")
                print(f"Test embedding type: {type(test_embedding)}")
                print(f"Test embedding length: {len(test_embedding)}")
                
                # Try the exact same query that's failing
                try:
                    similarity_result = session.run("""
                    MATCH (m:Memory {id: $memory_id})
                    WHERE m.embedding IS NOT NULL
                    WITH m, vector.similarity.cosine(m.embedding, $test_embedding) AS similarity
                    RETURN similarity
                    """, memory_id=memory_id, test_embedding=test_embedding)
                    
                    sim_record = similarity_result.single()
                    if sim_record:
                        print(f"SUCCESS: Similarity = {sim_record['similarity']}")
                    else:
                        print("FAILED: No similarity result returned")
                        
                except Exception as e:
                    print(f"FAILED: {e}")
                    
                    # Check if it's a data type issue by converting to proper format
                    print("Attempting format conversion...")
                    
                    # Ensure both embeddings are proper Python lists of floats
                    fixed_stored = [float(x) for x in stored_embedding]
                    fixed_test = [float(x) for x in test_embedding]
                    
                    try:
                        # Update the stored embedding with proper format
                        session.run("""
                        MATCH (m:Memory {id: $memory_id})
                        SET m.embedding = $fixed_embedding
                        """, memory_id=memory_id, fixed_embedding=fixed_stored)
                        
                        print("Updated stored embedding format")
                        
                        # Test again
                        retry_result = session.run("""
                        MATCH (m:Memory {id: $memory_id})
                        WHERE m.embedding IS NOT NULL
                        WITH m, vector.similarity.cosine(m.embedding, $test_embedding) AS similarity
                        RETURN similarity
                        """, memory_id=memory_id, test_embedding=fixed_test)
                        
                        retry_record = retry_result.single()
                        if retry_record:
                            print(f"SUCCESS after fix: Similarity = {retry_record['similarity']}")
                            
                            # Apply fix to all embeddings
                            print("Applying fix to all embeddings...")
                            session.run("""
                            MATCH (n)
                            WHERE n.embedding IS NOT NULL
                            SET n.embedding = [x IN n.embedding | toFloat(x)]
                            """)
                            print("All embeddings converted to proper float format")
                            
                        else:
                            print("Still failing after format conversion")
                            
                    except Exception as fix_error:
                        print(f"Format conversion failed: {fix_error}")
            
            else:
                print("No memories with embeddings found")
        
        driver.close()
        
    except Exception as e:
        print(f"Fix attempt failed: {e}")

if __name__ == "__main__":
    fix_vector_similarity()