#!/usr/bin/env python3
"""
Neural Memory System for NeuroLM
Hierarchical topic-based memory that mimics human cognitive organization
"""

import os
import uuid
from neo4j import GraphDatabase
from utils import generate_embedding
from typing import List, Dict, Any, Optional
import json
import openai

class NeuralMemorySystem:
    """Hierarchical topic-based memory system"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
        self.openai_client = openai.OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        # Simple cache for topic extraction results
        self._topic_cache = {}
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema and constraints"""
        with self.driver.session() as session:
            # Create constraints
            session.run("CREATE CONSTRAINT user_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            session.run("CREATE CONSTRAINT topic_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE")
            session.run("CREATE CONSTRAINT memory_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE")
            
            # Create vector indexes for semantic search
            try:
                session.run("CREATE VECTOR INDEX memory_embeddings IF NOT EXISTS FOR (m:Memory) ON (m.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}")
                session.run("CREATE VECTOR INDEX topic_embeddings IF NOT EXISTS FOR (t:Topic) ON (t.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}")
            except:
                pass  # Indexes might already exist
    
    def create_user(self, user_id: str, username: str = None) -> bool:
        """Create a user node"""
        try:
            with self.driver.session() as session:
                session.run("""
                MERGE (u:User {id: $user_id})
                SET u.username = $username, u.created_at = datetime()
                """, user_id=user_id, username=username or user_id)
                return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def extract_topics(self, content: str) -> list:
        """Extract multiple topics from conversation content using Gemini 2.0 Flash"""
        # Check cache first (simple hash-based caching)
        content_hash = str(hash(content[:200]))  # Use first 200 chars for cache key
        if content_hash in self._topic_cache:
            return self._topic_cache[content_hash]
            
        try:
            # Try Gemini 2.0 Flash first
            response = self.openai_client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[
                    {"role": "system", "content": "Extract 1-3 main topics from this conversation. Avoid creating separate topics for related concepts (e.g., 'Fitness' and 'Health' for workout discussions should be 'Health & Fitness'). Format: 'Primary: TopicName, Secondary: TopicName, Tertiary: TopicName' (only include what's relevant). Examples: 'Primary: Health & Fitness' or 'Primary: Cooking, Secondary: Nutrition'. Use 1-4 words per topic, consolidate related concepts."},
                    {"role": "user", "content": content}
                ],
                temperature=0.2,
                max_tokens=40
            )
            
            response_text = response.choices[0].message.content.strip()
            topics = []
            
            # Parse the response to extract topics
            if response_text:
                parts = response_text.split(',')
                for part in parts:
                    if ':' in part:
                        topic = part.split(':', 1)[1].strip()
                        if topic and len(topics) < 3:
                            topics.append(topic)
            
            result = topics if topics else ["General Discussion"]
            # Cache the result
            self._topic_cache[content_hash] = result
            # Keep cache size manageable 
            if len(self._topic_cache) > 100:
                # Remove oldest entries (simple FIFO)
                oldest_key = next(iter(self._topic_cache))
                del self._topic_cache[oldest_key]
            return result
            
        except Exception as e:
            print(f"Gemini topic extraction failed, trying fallback: {e}")
            # Fallback to GPT-4o Mini
            try:
                response = self.openai_client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Extract 1-3 main topics from this conversation. Avoid creating separate topics for related concepts (e.g., 'Fitness' and 'Health' for workout discussions should be 'Health & Fitness'). Format: 'Primary: TopicName, Secondary: TopicName, Tertiary: TopicName' (only include what's relevant). Use 1-4 words per topic, consolidate related concepts."},
                        {"role": "user", "content": content}
                    ],
                    temperature=0.2,
                    max_tokens=40
                )
                
                response_text = response.choices[0].message.content.strip()
                topics = []
                
                if response_text:
                    parts = response_text.split(',')
                    for part in parts:
                        if ':' in part:
                            topic = part.split(':', 1)[1].strip()
                            if topic and len(topics) < 3:
                                topics.append(topic)
                
                result = topics if topics else ["General Discussion"]
                # Cache fallback result too
                self._topic_cache[content_hash] = result
                return result
                
            except Exception as fallback_error:
                print(f"All topic extraction failed: {fallback_error}")
                result = ["General Discussion"]
                self._topic_cache[content_hash] = result
                return result
    
    def find_or_create_topic(self, user_id: str, topic_name: str, content: str) -> str:
        """Find existing topic or create new one with enhanced collision detection"""
        try:
            topic_embedding = generate_embedding(f"{topic_name} {content}")
            topic_id = str(uuid.uuid4())
            
            with self.driver.session() as session:
                # Enhanced similarity check with name matching
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)
                WHERE t.embedding IS NOT NULL
                WITH t, 
                     vector.similarity.cosine(t.embedding, $topic_embedding) AS similarity,
                     CASE 
                         WHEN toLower(t.name) CONTAINS toLower($topic_name) OR toLower($topic_name) CONTAINS toLower(t.name) 
                         THEN 0.2 
                         ELSE 0.0 
                     END AS name_bonus
                WHERE similarity + name_bonus > 0.75
                RETURN t.id as topic_id, t.name as name, similarity + name_bonus as final_score
                ORDER BY final_score DESC
                LIMIT 1
                """, user_id=user_id, topic_embedding=topic_embedding, topic_name=topic_name)
                
                existing = result.single()
                if existing:
                    print(f"Found existing topic: {existing['name']} (score: {existing['final_score']:.3f})")
                    return existing['topic_id']
                
                # Create new topic
                session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (t:Topic {
                    id: $topic_id,
                    name: $topic_name,
                    embedding: $topic_embedding,
                    created_at: datetime(),
                    memory_count: 0
                })
                CREATE (u)-[:HAS_TOPIC]->(t)
                """, user_id=user_id, topic_id=topic_id, topic_name=topic_name, topic_embedding=topic_embedding)
                
                print(f"Created new topic: {topic_name}")
                return topic_id
                
        except Exception as e:
            print(f"Error finding/creating topic: {e}")
            return None
    
    def store_conversation(self, user_id: str, role: str, content: str) -> Optional[str]:
        """Store conversation in hierarchical topic structure"""
        try:
            # Extract multiple topics from content
            topics = self.extract_topics(content)
            
            # Generate embedding for content
            content_embedding = generate_embedding(content)
            memory_id = str(uuid.uuid4())
            
            # Create memory node first
            with self.driver.session() as session:
                session.run("""
                CREATE (m:Memory {
                    id: $memory_id,
                    role: $role,
                    content: $content,
                    embedding: $content_embedding,
                    created_at: datetime(),
                    access_count: 0,
                    relevance_score: 1.0
                })
                """, memory_id=memory_id, role=role, content=content, content_embedding=content_embedding)
            
            # Connect memory to all relevant topics
            for topic_name in topics:
                topic_id = self.find_or_create_topic(user_id, topic_name, content)
                if topic_id:
                    with self.driver.session() as session:
                        session.run("""
                        MATCH (t:Topic {id: $topic_id}), (m:Memory {id: $memory_id})
                        CREATE (t)-[:CONTAINS_MEMORY]->(m)
                        SET t.memory_count = t.memory_count + 1,
                            t.last_updated = datetime()
                        """, topic_id=topic_id, memory_id=memory_id)
                
            # Create cross-topic links if content references other topics  
            self._create_cross_topic_links(memory_id, content, user_id)
            
            return memory_id
                
        except Exception as e:
            print(f"Error storing conversation: {e}")
            return None
    
    def _create_cross_topic_links(self, memory_id: str, content: str, user_id: str):
        """Create links between memories across different topics"""
        try:
            content_embedding = generate_embedding(content)
            
            with self.driver.session() as session:
                
                # Debug embedding before vector similarity
                print(f"Content embedding type: {type(content_embedding)}, length: {len(content_embedding) if content_embedding else 'None'}")
                
                # Find semantically similar memories in other topics
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                WHERE m.id <> $memory_id AND m.embedding IS NOT NULL
                WITH m, vector.similarity.cosine(m.embedding, $content_embedding) AS similarity
                WHERE similarity > 0.75
                RETURN m.id as related_memory_id, similarity
                ORDER BY similarity DESC
                LIMIT 3
                """, user_id=user_id, memory_id=memory_id, content_embedding=content_embedding)
                
                # Create relationships to related memories
                for record in result:
                    session.run("""
                    MATCH (m1:Memory {id: $memory_id}), (m2:Memory {id: $related_memory_id})
                    CREATE (m1)-[:RELATES_TO {strength: $similarity}]->(m2)
                    """, memory_id=memory_id, related_memory_id=record['related_memory_id'], similarity=record['similarity'])
                    
        except Exception as e:
            print(f"Error creating cross-topic links: {e}")
    
    def retrieve_context(self, user_id: str, query: str, limit: int = 5) -> str:
        """Retrieve contextual memories using topic hierarchy"""
        try:
            query_embedding = generate_embedding(query)
            context_parts = []
            
            with self.driver.session() as session:
                # Find relevant topics first
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)
                WHERE t.embedding IS NOT NULL
                WITH t, vector.similarity.cosine(t.embedding, $query_embedding) AS topic_similarity
                WHERE topic_similarity > 0.6
                
                // Get memories from relevant topics
                MATCH (t)-[:CONTAINS_MEMORY]->(m:Memory)
                WHERE m.embedding IS NOT NULL
                WITH t, m, topic_similarity, vector.similarity.cosine(m.embedding, $query_embedding) AS memory_similarity
                
                // Combined scoring: topic relevance + memory relevance
                WITH t, m, (topic_similarity * 0.3 + memory_similarity * 0.7) AS combined_score
                WHERE combined_score > 0.6
                
                RETURN t.name as topic, m.role as role, m.content as content, combined_score
                ORDER BY combined_score DESC
                LIMIT $limit
                """, user_id=user_id, query_embedding=query_embedding, limit=limit)
                
                # Group by topics
                topics = {}
                for record in result:
                    topic = record['topic']
                    if topic not in topics:
                        topics[topic] = []
                    topics[topic].append(f"- {record['role']}: {record['content']}")
                
                # Format context with better organization
                for topic, memories in topics.items():
                    context_parts.append(f"From {topic}:")
                    context_parts.extend(memories)
                
                return "\n".join(context_parts) if context_parts else ""
                
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return ""
    
    def get_topic_overview(self, user_id: str) -> Dict[str, Any]:
        """Get overview of user's topic structure"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)
                OPTIONAL MATCH (t)-[:CONTAINS_MEMORY]->(m:Memory)
                RETURN t.name as topic, t.created_at as created, count(m) as memory_count
                ORDER BY memory_count DESC, created DESC
                """, user_id=user_id)
                
                topics = []
                for record in result:
                    topics.append({
                        'name': record['topic'],
                        'memory_count': record['memory_count'],
                        'created': record['created']
                    })
                
                return {'topics': topics, 'total_topics': len(topics)}
                
        except Exception as e:
            print(f"Error getting topic overview: {e}")
            return {"topics": [], "topic_count": 0, "total_memories": 0}
    
    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for compatibility with app interface"""
        overview = self.get_topic_overview(user_id)
        return {
            "total_memories": overview["total_memories"],
            "top_topics": overview["topics"][:5],
            "avg_confidence": 0.85,  # Default confidence level
            "total_links": 0  # Cross-topic links count
        }

    def get_conversation_history(self, user_id: str, limit: int = 10) -> list:
        """Get recent conversation history for compatibility"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                RETURN m.role as role, m.content as content, m.created_at as timestamp
                ORDER BY m.created_at DESC
                LIMIT $limit
                """, user_id=user_id, limit=limit)
                
                return [{"role": record["role"], "content": record["content"], "timestamp": record["timestamp"]} 
                       for record in result]
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []

    def get_memory_count(self, user_id: str) -> int:
        """Get total memory count"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                RETURN count(m) as count
                """, user_id=user_id)
                
                record = result.single()
                return record["count"] if record else 0
        except Exception as e:
            print(f"Error getting memory count: {e}")
            return 0

    def get_relevant_memories(self, user_id: str, query: str, limit: int = 5) -> list:
        """Get relevant memories for a query"""
        context = self.retrieve_context(user_id, query, limit)
        if context:
            return [{"content": context, "relevance": 0.8}]
        return []

    def store_chat(self, user_id: str, messages: list):
        """Store chat messages in the neural memory system"""
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                self.store_conversation(user_id, msg["role"], msg["content"])

    def cleanup_invalid_embeddings(self):
        """Clean up invalid embeddings that cause vector similarity errors"""
        try:
            with self.driver.session() as session:
                # Find memories with invalid embeddings
                result = session.run("""
                MATCH (m:Memory)
                WHERE m.embedding IS NOT NULL 
                AND (size(m.embedding) <> 1536 OR NOT all(x IN m.embedding WHERE x IS NOT NULL))
                RETURN m.id as memory_id, size(m.embedding) as embedding_size
                """)
                
                invalid_memories = list(result)
                print(f"Found {len(invalid_memories)} memories with invalid embeddings")
                
                # Fix invalid memory embeddings
                for record in invalid_memories:
                    memory_id = record['memory_id']
                    # Get memory content to regenerate embedding
                    content_result = session.run("""
                    MATCH (m:Memory {id: $memory_id})
                    RETURN m.content as content
                    """, memory_id=memory_id)
                    
                    content_record = content_result.single()
                    if content_record:
                        content = content_record['content']
                        new_embedding = generate_embedding(content)
                        
                        if new_embedding and isinstance(new_embedding, list) and len(new_embedding) == 1536:
                            session.run("""
                            MATCH (m:Memory {id: $memory_id})
                            SET m.embedding = $new_embedding
                            """, memory_id=memory_id, new_embedding=new_embedding)
                            print(f"Fixed embedding for memory {memory_id}")
                        else:
                            # Remove invalid embedding
                            session.run("""
                            MATCH (m:Memory {id: $memory_id})
                            REMOVE m.embedding
                            """, memory_id=memory_id)
                            print(f"Removed invalid embedding for memory {memory_id}")
                
                # Find and fix invalid topic embeddings
                topic_result = session.run("""
                MATCH (t:Topic)
                WHERE t.embedding IS NOT NULL 
                AND (size(t.embedding) <> 1536 OR NOT all(x IN t.embedding WHERE x IS NOT NULL))
                RETURN t.id as topic_id, t.name as topic_name, size(t.embedding) as embedding_size
                """)
                
                invalid_topics = list(topic_result)
                print(f"Found {len(invalid_topics)} topics with invalid embeddings")
                
                for record in invalid_topics:
                    topic_id = record['topic_id']
                    topic_name = record['topic_name']
                    new_embedding = generate_embedding(topic_name)
                    
                    if new_embedding and isinstance(new_embedding, list) and len(new_embedding) == 1536:
                        session.run("""
                        MATCH (t:Topic {id: $topic_id})
                        SET t.embedding = $new_embedding
                        """, topic_id=topic_id, new_embedding=new_embedding)
                        print(f"Fixed embedding for topic {topic_name}")
                    else:
                        session.run("""
                        MATCH (t:Topic {id: $topic_id})
                        REMOVE t.embedding
                        """, topic_id=topic_id)
                        print(f"Removed invalid embedding for topic {topic_name}")
                
                print("Embedding cleanup completed")
                
        except Exception as e:
            print(f"Error during embedding cleanup: {e}")

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()