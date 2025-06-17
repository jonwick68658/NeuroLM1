"""
Intelligent Memory System - Core Implementation
Replaces the existing memory system with intelligent routing and fast retrieval
"""

import re
import json
import asyncio
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
from neo4j import GraphDatabase
import openai
import os
from utils import generate_embedding

class MemoryIntent(Enum):
    """Classification of user query intent for memory routing"""
    RECALL_PERSONAL = "recall_personal"      # "What did I tell you about my job?"
    RECALL_FACTUAL = "recall_factual"        # "What's my email address?"
    GENERAL_KNOWLEDGE = "general_knowledge"   # "What's the weather like?"
    CONTEXTUAL = "contextual"                # "How does this relate to..."
    STORE_FACT = "store_fact"                # "My birthday is..."

class MemoryRouter:
    """Fast intent classification for memory routing"""
    
    def __init__(self):
        # Pattern-based classification (can be upgraded to ML model later)
        self.patterns = {
            MemoryIntent.RECALL_PERSONAL: [
                r'\b(what did i tell you|do you remember|you know that i|i mentioned|we discussed)\b',
                r'\b(remember when|you said|i told you|as i said)\b'
            ],
            MemoryIntent.RECALL_FACTUAL: [
                r'\b(what\'s my|my email|my phone|my address|my birthday)\b',
                r'\b(my name is|i am|i work at|i live in)\b'
            ],
            MemoryIntent.CONTEXTUAL: [
                r'\b(how does this relate|like we talked about|similar to what)\b',
                r'\b(based on what|given what we discussed)\b'
            ],
            MemoryIntent.STORE_FACT: [
                r'\b(my .* is|i am|i work|i live|i like|i don\'t like)\b',
                r'\b(remember that|just so you know|for future reference)\b'
            ]
        }
    
    def classify_intent(self, text: str) -> MemoryIntent:
        """Classify user intent for memory routing"""
        text_lower = text.lower()
        
        # Check each intent pattern
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent
        
        # Default to general knowledge if no memory patterns found
        return MemoryIntent.GENERAL_KNOWLEDGE
    
    def should_use_memory(self, intent: MemoryIntent) -> bool:
        """Determine if memory retrieval is needed"""
        return intent in [
            MemoryIntent.RECALL_PERSONAL,
            MemoryIntent.RECALL_FACTUAL,
            MemoryIntent.CONTEXTUAL
        ]

class ImportanceScorer:
    """Score the importance of content for memory storage"""
    
    def score_importance(self, content: str, context: str = "") -> float:
        """Multi-factor importance scoring"""
        score = 0.0
        content_lower = content.lower()
        
        # Personal information indicators (high importance)
        personal_patterns = [
            r'\b(my name is|i am|i work at|i live in|my email|my phone)\b',
            r'\b(my birthday|my address|my job|my family|my wife|my husband)\b'
        ]
        for pattern in personal_patterns:
            if re.search(pattern, content_lower):
                score += 0.4
                break
        
        # Preferences and opinions (medium-high importance)
        preference_words = ['love', 'hate', 'like', 'dislike', 'prefer', 'favorite', 'important']
        if any(word in content_lower for word in preference_words):
            score += 0.3
        
        # Specific details (dates, numbers, proper nouns)
        specificity_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # dates
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # proper nouns
            r'\b\d+\b'  # numbers
        ]
        for pattern in specificity_patterns:
            if re.search(pattern, content):
                score += 0.1
                break
        
        # Future references
        future_words = ['tomorrow', 'next week', 'remember', 'remind', 'later', 'upcoming']
        if any(word in content_lower for word in future_words):
            score += 0.2
        
        return min(score, 1.0)

class IntelligentMemorySystem:
    """Main intelligent memory system"""
    
    def __init__(self):
        self.router = MemoryRouter()
        self.scorer = ImportanceScorer()
        
        # Neo4j connection (reuse existing)
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        self._setup_vector_index()
    
    def _setup_vector_index(self):
        """Setup Neo4j vector index for fast semantic search"""
        try:
            with self.driver.session() as session:
                # Create vector index for memory nodes
                session.run("""
                    CREATE VECTOR INDEX memory_embedding_index IF NOT EXISTS
                    FOR (m:IntelligentMemory) ON (m.embedding)
                    OPTIONS {indexConfig: {
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }}
                """)
                print("✅ Vector index created successfully")
        except Exception as e:
            print(f"❌ Vector index setup failed: {e}")
    
    async def store_memory(self, content: str, user_id: str, conversation_id: str, 
                          message_type: str = "user") -> Optional[str]:
        """Store memory with intelligent importance scoring"""
        
        # Score importance
        importance = self.scorer.score_importance(content)
        
        # Only store if importance is above threshold
        if importance < 0.1:
            return None
        
        # Generate embedding
        embedding = generate_embedding(content)
        if not embedding:
            return None
        
        # Store in Neo4j
        try:
            with self.driver.session() as session:
                result = session.run("""
                    CREATE (m:IntelligentMemory {
                        id: randomUUID(),
                        content: $content,
                        user_id: $user_id,
                        conversation_id: $conversation_id,
                        message_type: $message_type,
                        importance: $importance,
                        embedding: $embedding,
                        timestamp: datetime(),
                        created_at: datetime()
                    })
                    RETURN m.id AS memory_id
                """, {
                    'content': content,
                    'user_id': user_id,
                    'conversation_id': conversation_id,
                    'message_type': message_type,
                    'importance': importance,
                    'embedding': embedding
                })
                
                record = result.single()
                return record['memory_id'] if record else None
                
        except Exception as e:
            print(f"Error storing memory: {e}")
            return None
    
    async def retrieve_memory(self, query: str, user_id: str, conversation_id: str, 
                            limit: int = 5) -> str:
        """Intelligent memory retrieval using hybrid approach"""
        
        # Classify intent
        intent = self.router.classify_intent(query)
        
        # Skip memory retrieval for general knowledge queries
        if not self.router.should_use_memory(intent):
            return ""
        
        # Generate query embedding
        query_embedding = generate_embedding(query)
        if not query_embedding:
            return ""
        
        try:
            with self.driver.session() as session:
                # Hybrid retrieval: semantic similarity + recent conversation
                result = session.run("""
                    // Semantic similarity search
                    CALL db.index.vector.queryNodes('memory_embedding_index', $limit, $query_embedding)
                    YIELD node AS semantic_memory, score
                    WHERE semantic_memory.user_id = $user_id
                    
                    // Recent conversation window
                    WITH collect({
                        content: semantic_memory.content,
                        importance: semantic_memory.importance,
                        score: score,
                        timestamp: semantic_memory.timestamp,
                        type: 'semantic'
                    }) AS semantic_results
                    
                    MATCH (recent:IntelligentMemory)
                    WHERE recent.user_id = $user_id 
                    AND recent.conversation_id = $conversation_id
                    AND recent.timestamp > datetime() - duration('PT30M')
                    
                    WITH semantic_results + collect({
                        content: recent.content,
                        importance: recent.importance,
                        score: 0.5,
                        timestamp: recent.timestamp,
                        type: 'recent'
                    }) AS all_memories
                    
                    UNWIND all_memories AS memory
                    RETURN memory
                    ORDER BY memory.importance DESC, memory.score DESC, memory.timestamp DESC
                    LIMIT $limit
                """, {
                    'query_embedding': query_embedding,
                    'user_id': user_id,
                    'conversation_id': conversation_id,
                    'limit': limit
                })
                
                memories = []
                for record in result:
                    memory = record['memory']
                    memories.append(f"- {memory['content']}")
                
                return "\n".join(memories) if memories else ""
                
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return ""
    
    async def extract_facts_from_response(self, dialogue: str) -> List[Dict]:
        """Extract structured facts from conversation (simple regex approach)"""
        facts = []
        
        # Simple fact extraction patterns
        fact_patterns = [
            (r'my name is (\w+)', 'name', 'is'),
            (r'i work at (\w+)', 'job', 'works_at'),
            (r'i live in (\w+)', 'location', 'lives_in'),
            (r'my email is ([\w@.]+)', 'email', 'is'),
            (r'i like (\w+)', 'preference', 'likes'),
            (r'i don\'t like (\w+)', 'preference', 'dislikes')
        ]
        
        dialogue_lower = dialogue.lower()
        
        for pattern, subject_type, predicate in fact_patterns:
            matches = re.findall(pattern, dialogue_lower)
            for match in matches:
                facts.append({
                    'subject': subject_type,
                    'predicate': predicate,
                    'object': match
                })
        
        return facts
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()

# Global instance
intelligent_memory = IntelligentMemorySystem()