#!/usr/bin/env python3

import os
from neo4j import GraphDatabase

def clear_neo4j_database():
    """Clear all data from Neo4j database"""
    
    # Get Neo4j connection details from environment
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER") 
    password = os.getenv("NEO4J_PASSWORD")
    
    if not all([uri, user, password]):
        print("Error: Neo4j environment variables not found")
        return False
    
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # Delete all nodes and relationships
            result = session.run("MATCH (n) DETACH DELETE n")
            print("Successfully cleared all data from Neo4j database")
            
            # Verify database is empty
            count_result = session.run("MATCH (n) RETURN count(n) as count")
            count = count_result.single()["count"]
            print(f"Database now contains {count} nodes")
            
        driver.close()
        return True
        
    except Exception as e:
        print(f"Error clearing database: {str(e)}")
        return False

if __name__ == "__main__":
    clear_neo4j_database()