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
    
    def extract_topic(self, content: str) -> str:
        """Extract topic from conversation content using LLM"""
        try:
            response = self.openai_client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Extract a single, concise topic (1-3 words) from this conversation. Examples: 'Cooking', 'Travel Planning', 'Career Advice', 'Personal Health'. Respond with just the topic name."},
                    {"role": "user", "content": content}
                ],
                temperature=0.3,
                max_tokens=10
            )
            topic = response.choices[0].message.content.strip()
            return topic if topic else "General Discussion"
        except Exception as e:
            print(f"Topic extraction failed: {e}")
            return "General Discussion"
    
    def find_or_create_topic(self, user_id: str, topic_name: str, content: str) -> str:
        """Find existing topic or create new one"""
        try:
            topic_embedding = generate_embedding(f"{topic_name} {content}")
            topic_id = str(uuid.uuid4())
            
            with self.driver.session() as session:
                # Check for existing similar topic
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)
                WHERE t.embedding IS NOT NULL
                WITH t, vector.similarity.cosine(t.embedding, $topic_embedding) AS similarity
                WHERE similarity > 0.8
                RETURN t.id as topic_id, t.name as name, similarity
                ORDER BY similarity DESC
                LIMIT 1
                """, user_id=user_id, topic_embedding=topic_embedding)
                
                existing = result.single()
                if existing:
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
                
                return topic_id
                
        except Exception as e:
            print(f"Error finding/creating topic: {e}")
            return None
    
    def store_conversation(self, user_id: str, role: str, content: str) -> Optional[str]:
        """Store conversation in hierarchical topic structure"""
        try:
            # Extract topic from content
            topic_name = self.extract_topic(content)
            
            # Find or create topic
            topic_id = self.find_or_create_topic(user_id, topic_name, content)
            if not topic_id:
                return None
            
            # Generate embedding for content
            content_embedding = generate_embedding(content)
            memory_id = str(uuid.uuid4())
            
            with self.driver.session() as session:
                # Store memory linked to topic
                session.run("""
                MATCH (t:Topic {id: $topic_id})
                CREATE (m:Memory {
                    id: $memory_id,
                    role: $role,
                    content: $content,
                    embedding: $content_embedding,
                    created_at: datetime(),
                    access_count: 0,
                    relevance_score: 1.0
                })
                CREATE (t)-[:CONTAINS_MEMORY]->(m)
                SET t.memory_count = t.memory_count + 1,
                    t.last_updated = datetime()
                """, topic_id=topic_id, memory_id=memory_id, role=role, content=content, content_embedding=content_embedding)
                
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
                
                # Format context
                for topic, memories in topics.items():
                    context_parts.append(f"\nFrom {topic} discussions:")
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
            return {'topics': [], 'total_topics': 0}
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()