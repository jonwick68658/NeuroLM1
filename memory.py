from neo4j import GraphDatabase
import os
from utils import generate_embedding
import pytz
from datetime import datetime
import logging

class Neo4jMemory:
    def __init__(self):
        """Initialize Neo4j connection and database schema"""
        try:
            self.driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI"),
                auth=(os.getenv("NEO4J_USER"), 
                     os.getenv("NEO4J_PASSWORD"))
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            self._init_db()
            logging.info("Neo4j connection established successfully")
            
        except Exception as e:
            logging.error(f"Failed to connect to Neo4j: {str(e)}")
            raise Exception(f"Neo4j connection failed: {str(e)}")
    
    def _init_db(self):
        """Initialize database constraints and indexes"""
        with self.driver.session() as session:
            try:
                # Create constraints
                session.run("""
                CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE
                """)
                
                session.run("""
                CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE
                """)
                
                # Create vector index for embeddings
                session.run("""
                CREATE VECTOR INDEX memory_embeddings IF NOT EXISTS
                FOR (m:Memory) ON m.embedding
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 384,
                    `vector.similarity_function`: 'cosine'
                }}
                """)
                
                logging.info("Database schema initialized successfully")
                
            except Exception as e:
                logging.warning(f"Schema initialization warning: {str(e)}")
                # Continue even if constraints already exist
    
    def store_chat(self, user_id, role, content):
        """Store chat message with vector embedding"""
        try:
            embedding = generate_embedding(content)
            timestamp = datetime.now(pytz.utc).isoformat()
            
            with self.driver.session() as session:
                session.run("""
                MERGE (u:User {id: $user_id})
                WITH u
                CREATE (m:Memory {
                    id: randomUUID(),
                    role: $role,
                    type: 'chat',
                    content: $content,
                    timestamp: datetime($timestamp),
                    embedding: $embedding
                })
                CREATE (u)-[:CREATED]->(m)
                """, 
                user_id=user_id, 
                role=role, 
                content=content,
                timestamp=timestamp,
                embedding=embedding
                )
                
        except Exception as e:
            logging.error(f"Failed to store chat: {str(e)}")
            raise Exception(f"Chat storage failed: {str(e)}")
    
    def store_knowledge(self, user_id, content, source):
        """Store knowledge document chunk with vector embedding"""
        try:
            embedding = generate_embedding(content)
            timestamp = datetime.now(pytz.utc).isoformat()
            
            with self.driver.session() as session:
                session.run("""
                MERGE (u:User {id: $user_id})
                WITH u
                CREATE (m:Memory {
                    id: randomUUID(),
                    type: 'knowledge',
                    content: $content,
                    source: $source,
                    timestamp: datetime($timestamp),
                    embedding: $embedding
                })
                CREATE (u)-[:CREATED]->(m)
                """, 
                user_id=user_id, 
                content=content,
                source=source,
                timestamp=timestamp,
                embedding=embedding
                )
                
        except Exception as e:
            logging.error(f"Failed to store knowledge: {str(e)}")
            raise Exception(f"Knowledge storage failed: {str(e)}")
    
    def get_relevant_memories(self, query, user_id, limit=7):
        """Retrieve relevant memories using vector similarity search"""
        try:
            query_embedding = generate_embedding(query)
            
            with self.driver.session() as session:
                results = session.run("""
                CALL db.index.vector.queryNodes('memory_embeddings', $limit, $query_embedding) 
                YIELD node, score
                MATCH (node)<-[:CREATED]-(:User {id: $user_id})
                WHERE score > 0.3
                RETURN node.content AS content, score
                ORDER BY score DESC
                """, 
                query_embedding=query_embedding,
                user_id=user_id,
                limit=limit
                )
                
                memories = [record["content"] for record in results]
                return memories
                
        except Exception as e:
            logging.error(f"Failed to retrieve memories: {str(e)}")
            return []  # Return empty list instead of raising exception
    
    def get_memory_count(self, user_id):
        """Get total number of memories for a user"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                RETURN count(m) AS count
                """, user_id=user_id)
                
                record = result.single()
                return record["count"] if record else 0
                
        except Exception as e:
            logging.error(f"Failed to get memory count: {str(e)}")
            return 0
    
    def get_conversation_history(self, user_id, limit=20):
        """Retrieve recent conversation history"""
        try:
            with self.driver.session() as session:
                results = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                WHERE m.type = 'chat'
                RETURN m.role AS role, m.content AS content, m.timestamp AS timestamp
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """, user_id=user_id, limit=limit)
                
                history = []
                for record in results:
                    history.append({
                        "role": record["role"],
                        "content": record["content"],
                        "timestamp": record["timestamp"]
                    })
                
                return list(reversed(history))  # Return in chronological order
                
        except Exception as e:
            logging.error(f"Failed to get conversation history: {str(e)}")
            return []
    
    def clear_user_memories(self, user_id):
        """Clear all memories for a user (useful for testing)"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                DETACH DELETE m
                RETURN count(m) AS deleted_count
                """, user_id=user_id)
                
                record = result.single()
                return record["deleted_count"] if record else 0
                
        except Exception as e:
            logging.error(f"Failed to clear memories: {str(e)}")
            return 0
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
    
    def __del__(self):
        """Ensure connection is closed when object is destroyed"""
        self.close()
