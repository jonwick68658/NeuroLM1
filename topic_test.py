import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def check_topics_and_relationships():
    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        
        with driver.session() as session:
            # Check for Topic nodes
            result = session.run("MATCH (t:Topic) RETURN count(t) as topic_count")
            topic_count = result.single()["topic_count"]
            print(f"📚 Topic nodes: {topic_count}")
            
            # Check for ABOUT relationships
            result = session.run("MATCH ()-[r:ABOUT]->() RETURN count(r) as about_count")
            about_count = result.single()["about_count"]
            print(f"🔗 ABOUT relationships: {about_count}")
            
            # Check for ASSOCIATED_WITH relationships
            result = session.run("MATCH ()-[r:ASSOCIATED_WITH]->() RETURN count(r) as assoc_count")
            assoc_count = result.single()["assoc_count"]
            print(f"🕸️ ASSOCIATED_WITH relationships: {assoc_count}")
            
            # Check all relationship types
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in result]
            print(f"🔍 All relationship types: {rel_types}")
            
            # Check recent memories for debugging
            result = session.run("""
            MATCH (m:Memory) 
            RETURN m.content, m.timestamp 
            ORDER BY m.timestamp DESC 
            LIMIT 3
            """)
            print("\n📝 Recent memories:")
            for record in result:
                print(f"  - {record['m.content'][:50]}...")
        
        driver.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_topics_and_relationships()