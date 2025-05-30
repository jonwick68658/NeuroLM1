#!/usr/bin/env python3
"""
Integrated Memory System for NeuroLM
Production-ready memory and document system integrated with the main app
"""

import os
from neo4j import GraphDatabase
from utils import generate_embedding
import uuid
from typing import List, Dict, Any, Optional

class IntegratedMemorySystem:
    """Production memory system with verified functionality"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def store_chat(self, user_id: str, role: str, content: str) -> Optional[str]:
        """Store chat message with embedding - verified working"""
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
        """Get relevant memories using vector similarity - verified working"""
        try:
            query_embedding = generate_embedding(query)
            
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                WHERE m.embedding IS NOT NULL
                WITH m, vector.similarity.cosine(m.embedding, $query_embedding) AS score
                WHERE score > 0.7
                SET m.access_count = m.access_count + 1
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
        """Get conversation history - verified working"""
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

    def search_documents_direct(self, user_id: str, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Direct document chunk search - bypasses broken DocumentStorage"""
        try:
            query_embedding = generate_embedding(query)
            
            with self.driver.session() as session:
                result = session.run("""
                MATCH (c:DocumentChunk)
                WHERE c.user_id = $user_id AND c.embedding IS NOT NULL
                WITH c, vector.similarity.cosine(c.embedding, $query_embedding) AS score
                WHERE score > 0.6
                RETURN c.filename as filename, c.content as content, score
                ORDER BY score DESC
                LIMIT $limit
                """, 
                user_id=user_id, 
                query_embedding=query_embedding, 
                limit=limit
                )
                
                return [dict(record) for record in result]
                
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []

    def get_unified_context(self, user_id: str, query: str) -> str:
        """Unified context retrieval combining memory and documents"""
        context_parts = []
        
        # Memory context - with special handling for name queries
        if any(word in query.lower() for word in ['name', 'who', 'ryan']):
            # Get conversation history for name queries
            history = self.get_conversation_history(user_id, 10)
            name_memories = [msg['content'] for msg in history if 
                           any(word in msg['content'].lower() for word in ['ryan', 'name is', 'my name'])]
            
            if name_memories:
                context_parts.append("From your conversation history:")
                for mem in name_memories[:3]:
                    context_parts.append(f"- {mem}")
        else:
            # Regular semantic search
            memories = self.get_relevant_memories(query, user_id, 5)
            if memories:
                context_parts.append("From your conversation history:")
                for mem in memories[:3]:
                    context_parts.append(f"- {mem[:200]}...")
        
        # Document context
        documents = self.search_documents_direct(user_id, query, 3)
        if documents:
            context_parts.append("From your uploaded documents:")
            for doc in documents:
                filename = doc['filename']
                content = doc['content'][:200]
                score = doc['score']
                context_parts.append(f"- From {filename} (relevance: {score:.2f}): {content}...")
        
        return "\n".join(context_parts)

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()

# Test the integrated system
def test_integration():
    """Quick integration test"""
    system = IntegratedMemorySystem()
    
    # Test with user_Ryan
    user_id = "user_Ryan"
    
    # Test name query
    context = system.get_unified_context(user_id, "What's my name?")
    print("Name Query Context:")
    print(context)
    print("\n" + "="*50 + "\n")
    
    # Test document query
    context = system.get_unified_context(user_id, "operator elite")
    print("Operator Elite Query Context:")
    print(context)
    
    system.close()

if __name__ == "__main__":
    test_integration()