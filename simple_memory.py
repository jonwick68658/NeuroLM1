#!/usr/bin/env python3
"""
Simplified Memory System for NeuroLM
Clean implementation without document processing complexity
"""

import os
from neo4j import GraphDatabase
from utils import generate_embedding
import uuid
from typing import List, Dict, Any, Optional

class SimpleMemorySystem:
    """Clean memory system without document processing"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def store_chat(self, user_id: str, role: str, content: str) -> Optional[str]:
        """Store chat message with embedding"""
        try:
            embedding = generate_embedding(content)
            message_id = str(uuid.uuid4())
            
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (m:Memory {
                    id: $message_id,
                    user_id: $user_id,
                    role: $role,
                    content: $content,
                    embedding: $embedding,
                    timestamp: datetime(),
                    access_count: 0,
                    strength: 1.0
                })
                CREATE (u)-[:CREATED]->(m)
                RETURN m.id as memory_id
                """, 
                user_id=user_id, 
                message_id=message_id,
                role=role, 
                content=content, 
                embedding=embedding
                )
                
                record = result.single()
                return record['memory_id'] if record else None
                
        except Exception as e:
            print(f"Error storing chat: {e}")
            return None
    
    def get_relevant_memories(self, query: str, user_id: str, limit: int = 7) -> List[str]:
        """Get relevant memories using vector similarity"""
        try:
            query_embedding = generate_embedding(query)
            
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                WHERE m.embedding IS NOT NULL
                WITH m, vector.similarity.cosine(m.embedding, $query_embedding) AS score
                WHERE score > 0.6
                RETURN m.content as content
                ORDER BY score DESC
                LIMIT $limit
                """, 
                user_id=user_id, 
                query_embedding=query_embedding, 
                limit=limit
                )
                
                return [record['content'] for record in result]
                
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return []
    
    def get_conversation_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get conversation history"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                RETURN m.role as role, m.content as content, m.timestamp as timestamp
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """, user_id=user_id, limit=limit)
                
                return [dict(record) for record in result]
                
        except Exception as e:
            print(f"Error getting history: {e}")
            return []

    def get_memory_count(self, user_id: str) -> int:
        """Get total memory count for user"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                RETURN count(m) as count
                """, user_id=user_id)
                
                record = result.single()
                return record['count'] if record else 0
                
        except Exception as e:
            print(f"Error getting memory count: {e}")
            return 0

    def get_memory_stats(self, user_id: str) -> dict:
        """Get memory statistics for user"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                RETURN 
                    count(m) as total_memories,
                    count(CASE WHEN m.strength > 0.8 THEN 1 END) as strong_memories,
                    avg(m.strength) as avg_strength
                """, user_id=user_id)
                
                record = result.single()
                if record:
                    return {
                        'total_memories': record['total_memories'] or 0,
                        'strong_memories': record['strong_memories'] or 0,
                        'avg_strength': record['avg_strength'] or 0.0,
                        'top_topics': []  # Simplified - no topic analysis
                    }
                return {'total_memories': 0, 'strong_memories': 0, 'avg_strength': 0.0, 'top_topics': []}
                
        except Exception as e:
            print(f"Error getting memory stats: {e}")
            return {'total_memories': 0, 'strong_memories': 0, 'avg_strength': 0.0, 'top_topics': []}
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()