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
# Embedding generation function
def generate_embedding(text: str) -> List[float]:
    """Generate embeddings using OpenAI API"""
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding generation error: {e}")
        return []

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
                r'\b(remember when|you said|i told you|as i said)\b',
                r'\b(what do you know about my|tell me about my|what about my)\b',
                r'\b(about my|my.*\?|know.*about.*me)\b',
                r'\b(who am i|what is my name|my name)\b',
                r'\b(tell me about myself|about me|know me)\b',
                r'\b(can.*remember|memory|recall|information|conversations|talked)\b',
                r'\b(answer.*from.*earlier|previous.*conversations|what.*testing)\b'
            ],
            MemoryIntent.RECALL_FACTUAL: [
                r'\b(what\'s my|my email|my phone|my address|my birthday)\b',
                r'\b(where do i|what are my|who is my)\b',
                r'\b(my.*languages|my.*hobbies|my.*interests)\b'
            ],
            MemoryIntent.CONTEXTUAL: [
                r'\b(how does this relate|like we talked about|similar to what)\b',
                r'\b(based on what|given what we discussed)\b',
                r'\b(hello|hi|hey)\b'
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
        
        # Default to contextual for most queries - let memory system decide
        return MemoryIntent.CONTEXTUAL
    
    def should_use_memory(self, intent: MemoryIntent) -> bool:
        """Determine if memory retrieval is needed"""
        # Use memory for most queries - only skip obvious general knowledge
        return intent != MemoryIntent.GENERAL_KNOWLEDGE

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
        
        # RIAI Configuration
        self.evaluation_model = "mistralai/mistral-small-3.2-24b-instruct"
        
        # Neo4j connection (reuse existing)
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        self._setup_vector_index()
    
    async def evaluate_response(self, user_query: str, ai_response: str) -> Optional[float]:
        """Evaluate AI response quality using Mistral model (R(t) function)"""
        try:
            from model_service import ModelService
            model_service = ModelService()
            
            evaluation_prompt = f"""Rate this AI response quality on a scale of 1-10:

User Query: {user_query}
AI Response: {ai_response}

Scoring criteria:
- Relevance (answers the question directly)
- Accuracy (factually correct information)
- Helpfulness (actionable and useful)
- Completeness (thorough coverage of the topic)

Return only the numeric score as a decimal (e.g., 7.5):"""

            messages = [
                {"role": "system", "content": "You are an expert AI response evaluator. Rate responses objectively based on quality criteria."},
                {"role": "user", "content": evaluation_prompt}
            ]
            
            response = await model_service.chat_completion(
                messages=messages,
                model=self.evaluation_model,
                web_search=False
            )
            
            # Extract numeric score from response
            score_match = re.search(r'(\d+\.?\d*)', response.strip())
            if score_match:
                score = float(score_match.group(1))
                return min(max(score, 1.0), 10.0)  # Clamp between 1-10
            
            return None
            
        except Exception as e:
            print(f"Response evaluation error: {e}")
            return None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI API"""
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding generation error: {e}")
            return []
    
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
    
    async def store_memory(self, content: str, user_id: str, conversation_id: Optional[str], 
                          message_type: str = "user", message_id: Optional[int] = None) -> Optional[str]:
        """Store memory with intelligent importance scoring"""
        
        # Score importance
        importance = self.scorer.score_importance(content)
        
        # Only store if importance is above threshold
        if importance < 0.1:
            return None
        
        # Generate embedding
        embedding = self.generate_embedding(content)
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
                        message_id: $message_id,
                        importance: $importance,
                        embedding: $embedding,
                        quality_score: null,
                        evaluation_timestamp: null,
                        evaluation_model: null,
                        human_feedback_score: null,
                        human_feedback_type: null,
                        human_feedback_timestamp: null,
                        final_quality_score: null,
                        final_score_timestamp: null,
                        timestamp: datetime(),
                        created_at: datetime()
                    })
                    RETURN m.id AS memory_id
                """, {
                    'content': content,
                    'user_id': user_id,
                    'conversation_id': conversation_id or "",
                    'message_type': message_type,
                    'message_id': message_id,
                    'importance': importance,
                    'embedding': embedding
                })
                
                record = result.single()
                return record['memory_id'] if record else None
                
        except Exception as e:
            print(f"Error storing memory: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def update_memory_quality_score(self, memory_id: str, quality_score: float) -> bool:
        """Update quality score for a specific memory (RIAI scoring)"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:IntelligentMemory {id: $memory_id})
                    SET m.quality_score = $quality_score,
                        m.evaluation_timestamp = datetime(),
                        m.evaluation_model = $evaluation_model
                    RETURN m.id AS updated_id
                """, {
                    'memory_id': memory_id,
                    'quality_score': quality_score,
                    'evaluation_model': self.evaluation_model
                })
                
                return result.single() is not None
                
        except Exception as e:
            print(f"Error updating memory quality score: {e}")
            return False
    
    async def update_human_feedback(self, message_id, feedback_score: float, feedback_type: str, user_id: str) -> bool:
        """Update memory with human feedback (H(t) function) - Legacy method using PostgreSQL message_id"""
        try:
            with self.driver.session() as session:
                # Convert message_id to integer if it's a string representation
                try:
                    search_message_id = int(message_id) if isinstance(message_id, str) else message_id
                except (ValueError, TypeError):
                    search_message_id = message_id
                
                result = session.run("""
                    MATCH (m:IntelligentMemory {message_id: $message_id})
                    WHERE m.user_id = $user_id
                    SET m.human_feedback_score = $feedback_score,
                        m.human_feedback_type = $feedback_type,
                        m.human_feedback_timestamp = datetime()
                    RETURN m.id AS updated_id
                """, {
                    'message_id': search_message_id,
                    'feedback_score': feedback_score,
                    'feedback_type': feedback_type,
                    'user_id': user_id
                })
                
                return result.single() is not None
                
        except Exception as e:
            print(f"Error updating human feedback: {e}")
            return False
    
    async def update_human_feedback_by_node_id(self, node_id: str, feedback_score: float, feedback_type: str, user_id: str) -> bool:
        """Update memory with human feedback using Neo4j node ID directly (simplified approach)"""
        try:
            print(f"DEBUG: Attempting to update feedback for node_id={node_id}, user_id={user_id}")
            
            with self.driver.session() as session:
                # First, check if the node exists at all
                check_result = session.run("""
                    MATCH (m:IntelligentMemory {id: $node_id})
                    RETURN m.id AS node_id, m.user_id AS user_id
                """, {'node_id': node_id})
                
                check_record = check_result.single()
                if not check_record:
                    print(f"DEBUG: Node {node_id} not found in database")
                    return False
                
                print(f"DEBUG: Found node {check_record['node_id']} with user_id {check_record['user_id']}")
                
                # Now try the update
                result = session.run("""
                    MATCH (m:IntelligentMemory {id: $node_id})
                    WHERE m.user_id = $user_id
                    SET m.human_feedback_score = $feedback_score,
                        m.human_feedback_type = $feedback_type,
                        m.human_feedback_timestamp = datetime()
                    RETURN m.id AS updated_id
                """, {
                    'node_id': node_id,
                    'feedback_score': feedback_score,
                    'feedback_type': feedback_type,
                    'user_id': user_id
                })
                
                update_record = result.single()
                if update_record:
                    print(f"DEBUG: Successfully updated feedback for node {update_record['updated_id']}")
                    return True
                else:
                    print(f"DEBUG: Update failed - node exists but user_id mismatch or other condition failed")
                    return False
                
        except Exception as e:
            print(f"ERROR: Exception in update_human_feedback_by_node_id: {e}")
            return False
    
    def calculate_final_quality_score(self, r_t_score: Optional[float], h_t_score: Optional[float]) -> Optional[float]:
        """Calculate final quality score using f(R(t), H(t)) intelligence refinement function"""
        if r_t_score is None:
            # If no R(t) score yet, use neutral baseline if H(t) feedback exists
            if h_t_score is not None:
                r_t_score = 6.0  # Neutral baseline for immediate H(t) processing
            else:
                return None  # Wait for background R(t) evaluation
        
        # Human feedback weight factor (amplifies human signals)
        human_weight = 1.5
        
        if h_t_score is not None:
            # Combine R(t) and H(t) with weighted human feedback
            final_score = r_t_score + (h_t_score * human_weight)
            # Clamp between 1-10 range
            return max(1.0, min(10.0, final_score))
        else:
            # No human feedback, use R(t) only - still apply clamping
            return max(1.0, min(10.0, r_t_score))
    
    async def update_final_quality_score(self, memory_id: str, user_id: str, use_message_id: bool = False) -> bool:
        """Update final quality score for a memory using f(R(t), H(t))"""
        try:
            with self.driver.session() as session:
                # Get current R(t) and H(t) scores
                if use_message_id:
                    # Query by PostgreSQL message_id
                    query = """
                        MATCH (m:IntelligentMemory {message_id: $memory_id})
                        WHERE m.user_id = $user_id
                        RETURN m.id AS internal_id, 
                               m.quality_score AS r_t_score,
                               m.human_feedback_score AS h_t_score
                    """
                else:
                    # Query by Neo4j internal ID
                    query = """
                        MATCH (m:IntelligentMemory {id: $memory_id})
                        WHERE m.user_id = $user_id
                        RETURN m.id AS internal_id,
                               m.quality_score AS r_t_score,
                               m.human_feedback_score AS h_t_score
                    """
                
                # Convert memory_id to integer if using message_id and it's a string
                search_id = memory_id
                if use_message_id:
                    try:
                        search_id = int(memory_id) if isinstance(memory_id, str) else memory_id
                    except (ValueError, TypeError):
                        search_id = memory_id
                
                result = session.run(query, {
                    'memory_id': search_id,
                    'user_id': user_id
                })
                
                record = result.single()
                if not record:
                    return False
                
                internal_id = record['internal_id']
                r_t_score = record['r_t_score']
                h_t_score = record['h_t_score']
                
                # Calculate final quality score
                final_score = self.calculate_final_quality_score(r_t_score, h_t_score)
                
                if final_score is not None:
                    # Update memory with final quality score using internal Neo4j ID
                    update_result = session.run("""
                        MATCH (m:IntelligentMemory {id: $internal_id})
                        WHERE m.user_id = $user_id
                        SET m.final_quality_score = $final_score,
                            m.final_score_timestamp = datetime()
                        RETURN m.id AS updated_id
                    """, {
                        'internal_id': internal_id,
                        'user_id': user_id,
                        'final_score': final_score
                    })
                    
                    return update_result.single() is not None
                
                return False
                
        except Exception as e:
            print(f"Error updating final quality score: {e}")
            return False
    
    async def get_unscored_memories(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get memories that haven't been quality scored yet"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:IntelligentMemory)
                    WHERE m.user_id = $user_id 
                    AND m.quality_score IS NULL
                    AND m.message_type = 'assistant'
                    RETURN m.id AS memory_id, m.content AS content
                    ORDER BY m.timestamp DESC
                    LIMIT $limit
                """, {
                    'user_id': user_id,
                    'limit': limit
                })
                
                return [{'memory_id': record['memory_id'], 'content': record['content']} for record in result]
                
        except Exception as e:
            print(f"Error getting unscored memories: {e}")
            return []
    
    async def retrieve_memory(self, query: str, user_id: str, conversation_id: Optional[str], 
                            limit: int = 5) -> str:
        """Intelligent memory retrieval using hybrid approach"""
        
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
            with self.driver.session() as session:
                # Search raw memories with RIAI quality boost
                memories = []
                
                # Search memories with quality-boosted scoring
                memory_result = session.run("""
                    CALL db.index.vector.queryNodes('memory_embedding_index', $limit, $query_embedding)
                    YIELD node, score
                    WHERE node.user_id = $user_id AND score > 0.3
                    RETURN node.content AS content, 
                           score, 
                           'memory' as type,
                           node.final_quality_score AS final_quality_score,
                           CASE 
                               WHEN node.final_quality_score IS NOT NULL 
                               THEN node.final_quality_score * 0.2 + score * 0.8
                               ELSE score
                           END AS boosted_score
                    ORDER BY boosted_score DESC
                """, {
                    'query_embedding': query_embedding,
                    'user_id': user_id,
                    'limit': limit
                })
                
                for record in memory_result:
                    content = record['content']
                    score = record['score']
                    memories.append(f"Previous message: {content}")
                

                
                # Also get recent conversation context if no semantic matches
                if not memories and conversation_id:
                    recent_result = session.run("""
                        MATCH (m:IntelligentMemory)
                        WHERE m.user_id = $user_id 
                        AND m.conversation_id = $conversation_id
                        AND m.timestamp > datetime() - duration('PT1H')
                        RETURN m.content AS content, m.message_type AS type
                        ORDER BY m.timestamp DESC
                        LIMIT 5
                    """, {
                        'user_id': user_id,
                        'conversation_id': conversation_id
                    })
                    
                    for record in recent_result:
                        msg_type = record['type']
                        content = record['content']
                        if msg_type == 'user':
                            memories.append(f"User previously said: {content}")
                        else:
                            memories.append(f"You previously responded: {content}")
                
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
    
    async def score_unscored_memories_background(self, user_id: str) -> Dict[str, int]:
        """Background process to score any unscored memories"""
        try:
            unscored_memories = await self.get_unscored_memories(user_id, limit=20)
            scored_count = 0
            failed_count = 0
            
            for memory in unscored_memories:
                memory_id = memory['memory_id']
                content = memory['content']
                
                # For assistant messages, we need the user query to evaluate properly
                try:
                    # Get the user message that preceded this assistant response
                    with self.driver.session() as session:
                        result = session.run("""
                            MATCH (user_msg:IntelligentMemory)
                            WHERE user_msg.user_id = $user_id 
                            AND user_msg.message_type = 'user'
                            AND user_msg.timestamp < (
                                SELECT m.timestamp 
                                FROM IntelligentMemory m 
                                WHERE m.id = $memory_id
                            )
                            RETURN user_msg.content AS user_query
                            ORDER BY user_msg.timestamp DESC
                            LIMIT 1
                        """, {
                            'user_id': user_id,
                            'memory_id': memory_id
                        })
                        
                        user_record = result.single()
                        if user_record:
                            user_query = user_record['user_query']
                            
                            # Evaluate the response
                            quality_score = await self.evaluate_response(user_query, content)
                            
                            if quality_score is not None:
                                # Update with quality score
                                success = await self.update_memory_quality_score(memory_id, quality_score)
                                if success:
                                    scored_count += 1
                                    print(f"DEBUG: Background scored memory {memory_id}: {quality_score}/10")
                                else:
                                    failed_count += 1
                            else:
                                failed_count += 1
                        else:
                            # Skip memories without corresponding user queries
                            print(f"DEBUG: Skipping memory {memory_id} - no user query found")
                            
                except Exception as e:
                    print(f"Error scoring memory {memory_id}: {e}")
                    failed_count += 1
            
            return {
                'total_unscored': len(unscored_memories),
                'scored': scored_count,
                'failed': failed_count
            }
            
        except Exception as e:
            print(f"Background scoring error: {e}")
            return {'total_unscored': 0, 'scored': 0, 'failed': 0}
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()

# Global instance
intelligent_memory = IntelligentMemorySystem()