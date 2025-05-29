from neo4j import GraphDatabase
import os
from utils import generate_embedding
import pytz
from datetime import datetime, timedelta
import logging
import openai
import re

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
            
            # Initialize OpenRouter client for topic detection
            self.openai_client = openai.OpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1"
            )
            
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
                
                # Topic constraints for hybrid topic detection
                session.run("""
                CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE
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
                
                logging.info("Enhanced database schema initialized successfully")
                
            except Exception as e:
                logging.warning(f"Schema initialization warning: {str(e)}")
                # Continue even if constraints already exist

    def repair_schema(self):
        """Fix database schema issues and repair broken embeddings"""
        try:
            with self.driver.session() as session:
                # Drop and recreate vector index if needed
                try:
                    session.run("DROP INDEX memory_embeddings IF EXISTS")
                except:
                    pass
                
                session.run("""
                CREATE VECTOR INDEX memory_embeddings IF NOT EXISTS
                FOR (m:Memory) ON m.embedding
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 384, 
                    `vector.similarity_function`: 'cosine'
                }}
                """)
                
                # Fix any memories with empty or invalid embeddings
                result = session.run("""
                MATCH (m:Memory)
                WHERE m.embedding IS NULL OR size(m.embedding) <> 384
                RETURN count(m) as broken_count
                """)
                broken_count = result.single()["broken_count"]
                
                if broken_count > 0:
                    logging.info(f"Repairing {broken_count} memories with broken embeddings")
                    
                    # Update broken embeddings
                    session.run("""
                    MATCH (m:Memory)
                    WHERE m.embedding IS NULL OR size(m.embedding) <> 384
                    SET m.embedding = $default_embedding
                    """, default_embedding=generate_embedding("placeholder"))
                
                logging.info("Schema repair completed successfully")
                return True
                
        except Exception as e:
            logging.error(f"Schema repair failed: {str(e)}")
            return False

    def extract_topics_hybrid(self, content):
        """Hybrid topic extraction using OpenRouter AI + keyword fallback"""
        topics = []
        
        try:
            # Primary: Smart topic extraction using OpenRouter
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{
                    "role": "user", 
                    "content": f"Extract 2-3 main topics from this text as single words or short phrases (max 20 chars each). Return only the topics separated by commas, no explanations:\n\n{content[:500]}"
                }],
                temperature=0.3,
                max_tokens=50
            )
            
            ai_topics = response.choices[0].message.content.strip()
            topics.extend([topic.strip().lower() for topic in ai_topics.split(',') if topic.strip()])
            
        except Exception as e:
            logging.warning(f"AI topic extraction failed, using keyword fallback: {str(e)}")
        
        # Secondary: Keyword extraction fallback
        if not topics:
            # Simple keyword extraction
            words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
            # Filter common words and take most frequent
            stop_words = {'that', 'this', 'with', 'have', 'will', 'from', 'they', 'been', 'said', 'each', 'which', 'their', 'time', 'could', 'would', 'should', 'about', 'after', 'first', 'never', 'these', 'think', 'where', 'being', 'every'}
            keywords = [word for word in words if word not in stop_words]
            word_freq = {}
            for word in keywords:
                word_freq[word] = word_freq.get(word, 0) + 1
            topics = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:3]
        
        # Clean and limit topics
        clean_topics = []
        for topic in topics[:3]:
            if topic and len(topic) > 2 and len(topic) < 25:
                clean_topics.append(topic.lower().strip())
        
        return clean_topics or ['general']

    def store_chat(self, user_id, role, content):
        """Store chat message with vector embedding and biomemetic properties"""
        try:
            embedding = generate_embedding(content)
            timestamp = datetime.now(pytz.utc).isoformat()
            
            # Extract topics using hybrid approach
            topics = self.extract_topics_hybrid(content)
            
            with self.driver.session() as session:
                # Store memory with topic relationships
                session.run("""
                MERGE (u:User {id: $user_id})
                WITH u
                CREATE (m:Memory {
                    id: randomUUID(),
                    role: $role,
                    type: 'chat',
                    content: $content,
                    timestamp: datetime($timestamp),
                    embedding: $embedding,
                    confidence: 1.0,
                    access_count: 0,
                    last_accessed: datetime($timestamp),
                    importance_score: 0.5
                })
                CREATE (u)-[:CREATED]->(m)
                
                // Create topic relationships
                WITH m
                UNWIND $topics AS topic_name
                MERGE (t:Topic {name: topic_name})
                ON CREATE SET t.created = datetime($timestamp), t.mention_count = 1
                ON MATCH SET t.mention_count = coalesce(t.mention_count, 0) + 1, t.last_mentioned = datetime($timestamp)
                MERGE (m)-[r:ABOUT]->(t)
                ON CREATE SET r.relevance = 1.0, r.created = datetime($timestamp)
                
                // Enhanced associative linking with recent memories
                WITH m
                OPTIONAL MATCH (u2:User {id: $user_id})-[:CREATED]->(prev:Memory)
                WHERE prev.timestamp < datetime($timestamp) AND prev.type = 'chat'
                WITH m, prev
                ORDER BY prev.timestamp DESC
                LIMIT 3
                WHERE prev IS NOT NULL
                
                MERGE (prev)-[link:ASSOCIATED_WITH]->(m)
                ON CREATE SET 
                    link.strength = 0.6,
                    link.created = datetime($timestamp),
                    link.type = 'temporal'
                ON MATCH SET 
                    link.strength = link.strength * 0.9 + 0.1,
                    link.last_reinforced = datetime($timestamp)
                """, 
                user_id=user_id, 
                role=role, 
                content=content,
                timestamp=timestamp,
                embedding=embedding,
                topics=topics
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
        """Retrieve relevant memories using enhanced associative biomemetic search"""
        try:
            query_embedding = generate_embedding(query)
            
            with self.driver.session() as session:
                # SIMPLIFIED AND CORRECTED QUERY
                results = session.run("""
                CALL db.index.vector.queryNodes('memory_embeddings', $limit, $query_embedding) 
                YIELD node, score
                MATCH (node)<-[:CREATED]-(:User {id: $user_id})
                
                // Update access tracking for retrieved memories
                SET node.access_count = coalesce(node.access_count, 0) + 1,
                    node.last_accessed = datetime()
                
                RETURN node.content AS content, score
                ORDER BY score DESC
                LIMIT $limit
                """, 
                query_embedding=query_embedding,
                user_id=user_id,
                limit=limit
                )
                
                memories = [record["content"] for record in results]
                return memories[:limit]  # Ensure we don't exceed limit
                
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
    
    def reinforce_memories(self, user_id):
        """Biomemetic memory consolidation - strengthen/weaken memories based on usage"""
        try:
            with self.driver.session() as session:
                current_time = datetime.now(pytz.utc).isoformat()
                
                # Strengthen frequently accessed memories
                session.run("""
                MATCH (m:Memory)<-[:CREATED]-(:User {id: $user_id})
                WHERE coalesce(m.access_count, 0) > 2
                SET m.confidence = CASE WHEN coalesce(m.confidence, 1.0) * 1.05 > 1.0 THEN 1.0 ELSE coalesce(m.confidence, 1.0) * 1.05 END,
                    m.importance_score = CASE WHEN coalesce(m.importance_score, 0.5) + 0.1 > 1.0 THEN 1.0 ELSE coalesce(m.importance_score, 0.5) + 0.1 END
                """, user_id=user_id)
                
                # Weaken memories that haven't been accessed recently
                session.run("""
                MATCH (m:Memory)<-[:CREATED]-(:User {id: $user_id})
                WHERE m.last_accessed < datetime($cutoff_time)
                SET m.confidence = greatest(0.1, coalesce(m.confidence, 1.0) * 0.95),
                    m.importance_score = greatest(0.1, coalesce(m.importance_score, 0.5) * 0.98)
                """, 
                user_id=user_id,
                cutoff_time=(datetime.now(pytz.utc) - timedelta(days=7)).isoformat()
                )
                
                # Remove very weak memories (optional - commented out for safety)
                # session.run("""
                # MATCH (m:Memory)<-[:CREATED]-(:User {id: $user_id})
                # WHERE coalesce(m.confidence, 1.0) < 0.2
                # DETACH DELETE m
                # """, user_id=user_id)
                
                logging.info(f"Memory reinforcement completed for user {user_id}")
                
        except Exception as e:
            logging.error(f"Failed to reinforce memories: {str(e)}")

    def get_memory_stats(self, user_id):
        """Get advanced biomemetic memory statistics including topics and connections"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                OPTIONAL MATCH (m)-[assoc:ASSOCIATED_WITH]-(connected:Memory)
                OPTIONAL MATCH (m)-[:ABOUT]->(t:Topic)
                RETURN 
                    count(DISTINCT m) AS total_memories,
                    avg(coalesce(m.confidence, 1.0)) AS avg_confidence,
                    sum(coalesce(m.access_count, 0)) AS total_accesses,
                    count(CASE WHEN coalesce(m.access_count, 0) > 3 THEN 1 END) AS strong_memories,
                    count(DISTINCT assoc) AS total_connections,
                    avg(coalesce(assoc.strength, 0)) AS avg_connection_strength,
                    count(CASE WHEN coalesce(assoc.strength, 0) > 0.7 THEN 1 END) AS strong_connections,
                    count(DISTINCT t) AS total_topics
                """, user_id=user_id)
                
                # Get top topics
                topics_result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)-[:ABOUT]->(t:Topic)
                RETURN t.name AS topic, count(m) AS frequency
                ORDER BY frequency DESC
                LIMIT 5
                """, user_id=user_id)
                
                top_topics = [{"topic": record["topic"], "count": record["frequency"]} 
                            for record in topics_result]
                
                record = result.single()
                if record:
                    return {
                        "total_memories": record["total_memories"],
                        "avg_confidence": round(record["avg_confidence"] or 0, 3),
                        "total_accesses": record["total_accesses"],
                        "strong_memories": record["strong_memories"],
                        "total_connections": record["total_connections"],
                        "avg_connection_strength": round(record["avg_connection_strength"] or 0, 3),
                        "strong_connections": record["strong_connections"],
                        "total_topics": record["total_topics"],
                        "top_topics": top_topics
                    }
                return {
                    "total_memories": 0, "avg_confidence": 0, "total_accesses": 0, 
                    "strong_memories": 0, "total_connections": 0, 
                    "avg_connection_strength": 0, "strong_connections": 0,
                    "total_topics": 0, "top_topics": []
                }
                
        except Exception as e:
            logging.error(f"Failed to get memory stats: {str(e)}")
            return {
                "total_memories": 0, "avg_confidence": 0, "total_accesses": 0, 
                "strong_memories": 0, "total_connections": 0, 
                "avg_connection_strength": 0, "strong_connections": 0,
                "total_topics": 0, "top_topics": []
            }

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
