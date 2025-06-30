"""
Check what data exists in Neo4j for testing
"""

import os
from neo4j import GraphDatabase

def check_neo4j_data():
    """Check what data exists in Neo4j"""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session() as session:
            # Check all node types
            result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count")
            print("Node counts by label:")
            for record in result:
                print(f"  {record['labels']}: {record['count']}")
            
            # Check IntelligentMemory nodes specifically
            result = session.run("MATCH (m:IntelligentMemory) RETURN count(m) as total")
            memory_record = result.single()
            total_memories = memory_record['total'] if memory_record else 0
            print(f"\nTotal IntelligentMemory nodes: {total_memories}")
            
            if total_memories > 0:
                # Get sample memories for Ryan
                result = session.run("""
                    MATCH (m:IntelligentMemory) 
                    WHERE m.user_id = $user_id 
                    RETURN m.content as content, m.message_type as message_type, 
                           m.timestamp as timestamp, m.conversation_id as conversation_id
                    ORDER BY m.timestamp DESC 
                    LIMIT 5
                """, user_id="24ca19e0-4695-4d68-a0c1-6daa98d8128e")
                
                print(f"\nSample memories for Ryan:")
                for i, record in enumerate(result):
                    content = record['content'][:80] + "..." if len(record['content']) > 80 else record['content']
                    print(f"  {i+1}. [{record['message_type']}] {content}")
                    print(f"      Time: {record['timestamp']}, Conv: {record['conversation_id']}")
            
            # Check if any DailySummary nodes exist
            result = session.run("MATCH (s:DailySummary) RETURN count(s) as count")
            summary_count = result.single()['count']
            print(f"\nExisting DailySummary nodes: {summary_count}")
            
    finally:
        driver.close()

if __name__ == "__main__":
    check_neo4j_data()