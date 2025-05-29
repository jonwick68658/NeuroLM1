import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def test_neo4j_connection():
    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        
        with driver.session() as session:
            # Test basic connection
            result = session.run("RETURN 1 as test")
            print("✅ Neo4j connection successful!")
            
            # Check if any data exists
            result = session.run("MATCH (n) RETURN count(n) as total_nodes")
            count = result.single()["total_nodes"]
            print(f"📊 Total nodes in database: {count}")
            
            # Check specifically for Memory nodes
            result = session.run("MATCH (m:Memory) RETURN count(m) as memory_count")
            memory_count = result.single()["memory_count"]
            print(f"🧠 Memory nodes: {memory_count}")
            
            # Check for User nodes
            result = session.run("MATCH (u:User) RETURN count(u) as user_count")
            user_count = result.single()["user_count"]
            print(f"👤 User nodes: {user_count}")
            
            # Check relationships
            result = session.run("MATCH ()-[r:CREATED]->() RETURN count(r) as created_relationships")
            rel_count = result.single()["created_relationships"]
            print(f"🔗 CREATED relationships: {rel_count}")
            
        driver.close()
        
        if memory_count > 0:
            print("\n✅ YES - Your app IS using Neo4j for memory storage!")
        else:
            print("\n❌ NO - Neo4j is connected but no memory data found yet")
            
    except Exception as e:
        print(f"❌ Neo4j connection failed: {str(e)}")

if __name__ == "__main__":
    test_neo4j_connection()