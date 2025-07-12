"""
PostgreSQL Memory Adapter for NeuroLM
PostgreSQL + pgvector for intelligent memory storage
"""

import os
import asyncio
import asyncpg
import json
import hashlib
import re
from typing import List, Dict, Optional, Union
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
from openai import OpenAI

class MemoryIntent(Enum):
    """Classification of user query intent for memory routing"""
    RECALL_PERSONAL = "recall_personal"
    RECALL_FACTUAL = "recall_factual"
    GENERAL_KNOWLEDGE = "general_knowledge"
    CONTEXTUAL = "contextual"
    STORE_FACT = "store_fact"

class MemoryRouter:
    """Fast intent classification for memory routing"""
    
    def __init__(self):
        self.personal_keywords = ['my', 'me', 'i', 'myself', 'mine', 'personal']
        self.factual_keywords = ['what', 'when', 'where', 'who', 'how', 'tell me about']
        self.general_keywords = ['explain', 'define', 'what is', 'help me understand']
        
    def classify_intent(self, text: str) -> MemoryIntent:
        """Classify user intent for memory routing"""
        text_lower = text.lower()
        
        # Check for personal recall
        if any(keyword in text_lower for keyword in self.personal_keywords):
            if any(recall in text_lower for recall in ['remember', 'recall', 'told you', 'mentioned']):
                return MemoryIntent.RECALL_PERSONAL
        
        # Check for factual recall
        if any(keyword in text_lower for keyword in self.factual_keywords):
            return MemoryIntent.RECALL_FACTUAL
        
        # Check for general knowledge
        if any(keyword in text_lower for keyword in self.general_keywords):
            return MemoryIntent.GENERAL_KNOWLEDGE
        
        # Default to contextual
        return MemoryIntent.CONTEXTUAL
    
    def should_use_memory(self, intent: MemoryIntent) -> bool:
        """Determine if memory retrieval is needed"""
        return intent != MemoryIntent.GENERAL_KNOWLEDGE

class ImportanceScorer:
    """Score the importance of content for memory storage"""
    
    def score_importance(self, content: str, context: str = "") -> float:
        """Multi-factor importance scoring"""
        score = 0.5  # Base score
        
        # Length factor
        if len(content) > 100:
            score += 0.1
        if len(content) > 500:
            score += 0.1
        
        # Personal information indicators
        personal_indicators = ['my name', 'i work', 'i live', 'my email', 'my phone']
        if any(indicator in content.lower() for indicator in personal_indicators):
            score += 0.3
        
        # Question indicators
        if content.endswith('?'):
            score += 0.1
        
        # Code or technical content
        if any(keyword in content.lower() for keyword in ['def ', 'class ', 'import ', 'function']):
            score += 0.2
        
        return min(1.0, score)

class PostgreSQLMemorySystem:
    """PostgreSQL-based intelligent memory system with pgvector"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.router = MemoryRouter()
        self.importance_scorer = ImportanceScorer()
        self.pool = None
        
    async def initialize_pool(self):
        """Initialize the PostgreSQL connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
    
    async def close_pool(self):
        """Close the PostgreSQL connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI API"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []
    
    async def store_memory(self, content: str, user_id: str, conversation_id: Optional[str], 
                          message_type: str = "user", message_id: Optional[int] = None) -> Optional[str]:
        """Store memory with intelligent importance scoring"""
        try:
            # Generate embedding
            embedding = self.generate_embedding(content)
            if not embedding:
                return None
            
            # Score importance
            importance = self.importance_scorer.score_importance(content)
            
            # Skip storing if importance is too low
            if importance < 0.3:
                return None
            
            await self.initialize_pool()
            
            async with self.pool.acquire() as conn:
                # Insert memory with proper vector format
                memory_id = await conn.fetchval("""
                    INSERT INTO intelligent_memories 
                    (user_id, conversation_id, message_id, content, message_type, embedding, importance, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6::vector, $7, $8)
                    RETURNING id
                """, user_id, conversation_id, message_id, content, message_type, str(embedding), importance, datetime.now())
                
                print(f"✅ Memory stored: {memory_id}")
                return str(memory_id)
                
        except Exception as e:
            print(f"Error storing memory: {e}")
            return None
    
    async def retrieve_memory(self, query: str, user_id: str, conversation_id: Optional[str], 
                            limit: int = 5) -> str:
        """Intelligent memory retrieval using vector similarity"""
        
        # Classify intent
        intent = self.router.classify_intent(query)
        
        # Skip memory retrieval for general knowledge queries
        if not self.router.should_use_memory(intent):
            return ""
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        if not query_embedding:
            return ""
        
        try:
            await self.initialize_pool()
            
            async with self.pool.acquire() as conn:
                # Search memories with quality-boosted scoring
                memories = await conn.fetch("""
                    SELECT content, 
                           1 - (embedding <=> $1::vector) as similarity,
                           final_quality_score,
                           CASE 
                               WHEN final_quality_score IS NOT NULL 
                               THEN final_quality_score * 0.2 + (1 - (embedding <=> $1::vector)) * 0.8
                               ELSE 1 - (embedding <=> $1::vector)
                           END as boosted_score
                    FROM intelligent_memories 
                    WHERE user_id = $2 
                    AND (1 - (embedding <=> $1::vector)) > 0.3
                    ORDER BY boosted_score DESC 
                    LIMIT $3
                """, str(query_embedding), user_id, limit)
                
                memory_texts = []
                for record in memories:
                    content = record['content']
                    similarity = record['similarity']
                    memory_texts.append(f"Previous message: {content}")
                
                # Also get recent conversation context if no semantic matches
                if not memory_texts and conversation_id:
                    recent_memories = await conn.fetch("""
                        SELECT content, message_type
                        FROM intelligent_memories
                        WHERE user_id = $1 
                        AND conversation_id = $2
                        AND created_at > $3
                        ORDER BY created_at DESC
                        LIMIT 5
                    """, user_id, conversation_id, datetime.now() - timedelta(hours=1))
                    
                    for record in recent_memories:
                        msg_type = record['message_type']
                        content = record['content']
                        if msg_type == 'user':
                            memory_texts.append(f"User previously said: {content}")
                        else:
                            memory_texts.append(f"You previously responded: {content}")
                
                return "\n".join(memory_texts) if memory_texts else ""
                
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return ""
    
    async def update_memory_quality_score(self, memory_id: str, quality_score: float) -> bool:
        """Update quality score for a specific memory (RIAI scoring)"""
        try:
            await self.initialize_pool()
            
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE intelligent_memories 
                    SET r_t_score = $1, updated_at = $2
                    WHERE id = $3
                """, quality_score, datetime.now(), int(memory_id))
                
                return result == "UPDATE 1"
                
        except Exception as e:
            print(f"Error updating memory quality score: {e}")
            return False
    
    async def update_human_feedback_by_node_id(self, node_id: str, feedback_score: float, 
                                             feedback_type: str, user_id: str) -> bool:
        """Update memory with human feedback using memory ID"""
        try:
            await self.initialize_pool()
            
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE intelligent_memories 
                    SET h_t_score = $1, 
                        updated_at = $2
                    WHERE id = $3 AND user_id = $4
                """, feedback_score, datetime.now(), int(node_id), user_id)
                
                return result == "UPDATE 1"
                
        except Exception as e:
            print(f"Error updating human feedback: {e}")
            return False
    
    def calculate_final_quality_score(self, r_t_score: Optional[float], h_t_score: Optional[float]) -> Optional[float]:
        """Calculate final quality score using f(R(t), H(t)) intelligence refinement function"""
        if r_t_score is None and h_t_score is None:
            return None
        
        # Use default values if one score is missing
        r_t = r_t_score if r_t_score is not None else 0.5
        h_t = h_t_score if h_t_score is not None else 0.0
        
        # f(R(t), H(t)) = R(t) + 1.5 * H(t) (human feedback weighted higher)
        final_score = r_t + 1.5 * h_t
        
        # Clamp to [0, 1] range
        return max(0.0, min(1.0, final_score))
    
    async def update_final_quality_score(self, memory_id: str, user_id: str) -> bool:
        """Update final quality score for a memory using f(R(t), H(t))"""
        try:
            await self.initialize_pool()
            
            async with self.pool.acquire() as conn:
                # Get current R(t) and H(t) scores
                record = await conn.fetchrow("""
                    SELECT r_t_score, h_t_score
                    FROM intelligent_memories
                    WHERE id = $1 AND user_id = $2
                """, int(memory_id), user_id)
                
                if not record:
                    return False
                
                r_t_score = record['r_t_score']
                h_t_score = record['h_t_score']
                
                # Calculate final quality score
                final_score = self.calculate_final_quality_score(r_t_score, h_t_score)
                
                if final_score is not None:
                    result = await conn.execute("""
                        UPDATE intelligent_memories
                        SET final_quality_score = $1, updated_at = $2
                        WHERE id = $3 AND user_id = $4
                    """, final_score, datetime.now(), int(memory_id), user_id)
                    
                    return result == "UPDATE 1"
                
                return False
                
        except Exception as e:
            print(f"Error updating final quality score: {e}")
            return False
    
    async def get_unscored_memories(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get memories that haven't been quality scored yet"""
        try:
            await self.initialize_pool()
            
            async with self.pool.acquire() as conn:
                records = await conn.fetch("""
                    SELECT id, content
                    FROM intelligent_memories
                    WHERE user_id = $1 
                    AND r_t_score IS NULL
                    AND message_type = 'assistant'
                    ORDER BY created_at DESC
                    LIMIT $2
                """, user_id, limit)
                
                return [{'memory_id': str(record['id']), 'content': record['content']} for record in records]
                
        except Exception as e:
            print(f"Error getting unscored memories: {e}")
            return []
    
    async def evaluate_response(self, user_query: str, ai_response: str) -> Optional[float]:
        """Evaluate AI response quality using external model (R(t) function)"""
        try:
            # Use OpenRouter API for evaluation (same as current system)
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "mistralai/mistral-small-3.2-24b-instruct",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an AI response evaluator. Rate the quality of AI responses on a scale of 0.0 to 1.0 based on accuracy, helpfulness, and relevance. Respond with only the numeric score."
                            },
                            {
                                "role": "user",
                                "content": f"User Question: {user_query}\n\nAI Response: {ai_response}\n\nQuality Score (0.0-1.0):"
                            }
                        ]
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    score_text = data['choices'][0]['message']['content'].strip()
                    try:
                        score = float(score_text)
                        return max(0.0, min(1.0, score))
                    except ValueError:
                        return 0.5
                
        except Exception as e:
            print(f"Error evaluating response: {e}")
            return 0.5
    
    def close(self):
        """Close database connections"""
        if self.pool:
            asyncio.create_task(self.close_pool())