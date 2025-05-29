import os
import math
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
import numpy as np
from utils import generate_embedding
import config

class MemoryRetriever:
    """Advanced memory retrieval system with weighted scoring algorithm"""
    
    def __init__(self, driver, weights=None):
        self.driver = driver
        self.weights = weights or config.DEFAULT_RETRIEVAL_WEIGHTS
        self.max_accesses = 100  # Normalization factor for access frequency
        
    def calculate_vector_similarity(self, memory_embedding, query_embedding):
        """Calculate cosine similarity between embeddings"""
        try:
            if not memory_embedding or not query_embedding:
                return 0.0
            
            # Convert to numpy arrays
            mem_vec = np.array(memory_embedding)
            query_vec = np.array(query_embedding)
            
            # Calculate cosine similarity
            dot_product = np.dot(mem_vec, query_vec)
            norms = np.linalg.norm(mem_vec) * np.linalg.norm(query_vec)
            
            if norms == 0:
                return 0.0
                
            return dot_product / norms
            
        except Exception as e:
            logging.warning(f"Error calculating vector similarity: {e}")
            return 0.0
    
    def calculate_temporal_relevance(self, memory_timestamp, decay_days=30):
        """Calculate temporal relevance with exponential decay"""
        try:
            if not memory_timestamp:
                return 0.0
                
            # Handle Neo4j DateTime objects and strings
            if hasattr(memory_timestamp, 'to_native'):
                # Neo4j DateTime object
                memory_time = memory_timestamp.to_native()
            elif isinstance(memory_timestamp, str):
                memory_time = datetime.fromisoformat(memory_timestamp.replace('Z', '+00:00'))
            else:
                memory_time = memory_timestamp
                
            # Ensure both times are timezone-aware or naive
            now = datetime.now()
            if hasattr(memory_time, 'tzinfo') and memory_time.tzinfo:
                now = datetime.now(memory_time.tzinfo)
            
            # Calculate days since memory creation
            days_old = (now - memory_time).days
            
            # Exponential decay: newer memories score higher
            temporal_score = math.exp(-max(0, days_old) / decay_days)
            
            return min(1.0, temporal_score)
            
        except Exception as e:
            logging.warning(f"Error calculating temporal relevance: {e}")
            return 0.0
    
    def calculate_access_frequency_score(self, access_count):
        """Calculate normalized access frequency score"""
        try:
            if access_count is None or access_count < 0:
                return 0.0
                
            # Logarithmic normalization to prevent extremely accessed memories from dominating
            access_score = math.log(1 + access_count) / math.log(1 + self.max_accesses)
            
            return min(1.0, access_score)
            
        except Exception as e:
            logging.warning(f"Error calculating access frequency: {e}")
            return 0.0
    
    def calculate_association_strength(self, memory_id, user_id):
        """Calculate average association strength for a memory"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (m:Memory {id: $memory_id})<-[:CREATED]-(:User {id: $user_id})
                OPTIONAL MATCH (m)-[r:ASSOCIATED_WITH]-(other:Memory)
                WHERE EXISTS((other)<-[:CREATED]-(:User {id: $user_id}))
                WITH m, CASE 
                    WHEN count(r) > 0 THEN avg(r.strength) 
                    ELSE 0.0 
                END AS avg_strength
                RETURN avg_strength
                """, memory_id=memory_id, user_id=user_id)
                
                record = result.single()
                if record:
                    return float(record['avg_strength'] or 0.0)
                return 0.0
                
        except Exception as e:
            logging.warning(f"Error calculating association strength: {e}")
            return 0.0
    
    def calculate_composite_score(self, memory, query_embedding, user_id):
        """Calculate weighted composite score for memory relevance"""
        try:
            # Extract memory properties
            embedding = memory.get('embedding', [])
            timestamp = memory.get('timestamp')
            access_count = memory.get('access_count', 0)
            memory_id = memory.get('id')
            
            # Calculate individual components
            vector_sim = self.calculate_vector_similarity(embedding, query_embedding)
            temporal_rel = self.calculate_temporal_relevance(timestamp)
            access_freq = self.calculate_access_frequency_score(access_count)
            association_str = self.calculate_association_strength(memory_id, user_id)
            
            # Apply weights and calculate final score
            weights = self.weights
            composite_score = (
                weights['vector'] * vector_sim +
                weights['temporal'] * temporal_rel +
                weights['access'] * access_freq +
                weights['association'] * association_str
            )
            
            # Store component scores for debugging
            memory['_scores'] = {
                'vector': vector_sim,
                'temporal': temporal_rel,
                'access': access_freq,
                'association': association_str,
                'composite': composite_score
            }
            
            return composite_score
            
        except Exception as e:
            logging.error(f"Error calculating composite score: {e}")
            return 0.0
    
    def get_relevant_memories(self, query: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve most relevant memories using advanced scoring algorithm"""
        try:
            # Generate query embedding
            query_embedding = generate_embedding(query)
            if not query_embedding:
                logging.warning("Failed to generate query embedding")
                return []
            
            # Get candidate memories using vector index
            with self.driver.session() as session:
                # First get vector candidates (fixed for existing schema)
                vector_results = session.run("""
                CALL db.index.vector.queryNodes('memory_embeddings', $candidates, $embedding)
                YIELD node AS memory, score AS vector_score
                WHERE EXISTS((memory)<-[:CREATED]-(:User {id: $user_id}))
                RETURN memory {
                    .*, 
                    id: memory.id,
                    content: memory.content,
                    timestamp: memory.timestamp,
                    access_count: memory.access_count,
                    embedding: memory.embedding,
                    confidence: memory.confidence,
                    role: memory.role
                } AS memory_props
                """, 
                candidates=config.PERFORMANCE_CONFIG['vector_candidates'],
                embedding=query_embedding, 
                user_id=user_id)
                
                candidates = []
                for record in vector_results:
                    memory_props = record['memory_props']
                    if memory_props and memory_props.get('content'):
                        candidates.append(memory_props)
                
                if not candidates:
                    logging.info(f"No vector candidates found for user {user_id}")
                    return []
                
                # Calculate composite scores for all candidates
                scored_memories = []
                for memory in candidates:
                    score = self.calculate_composite_score(memory, query_embedding, user_id)
                    memory['relevance_score'] = score
                    scored_memories.append(memory)
                
                # Sort by composite score and return top results
                scored_memories.sort(key=lambda m: m['relevance_score'], reverse=True)
                top_memories = scored_memories[:limit]
                
                # Update access counts for retrieved memories
                memory_ids = [m['id'] for m in top_memories]
                if memory_ids:
                    session.run("""
                    MATCH (m:Memory)<-[:CREATED]-(:User {id: $user_id})
                    WHERE m.id IN $memory_ids
                    SET m.access_count = COALESCE(m.access_count, 0) + 1,
                        m.last_accessed = datetime()
                    """, memory_ids=memory_ids, user_id=user_id)
                
                logging.info(f"Retrieved {len(top_memories)} relevant memories for query")
                return top_memories
                
        except Exception as e:
            logging.error(f"Error in get_relevant_memories: {e}")
            return []
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Update retrieval weights and validate they sum to 1.0"""
        try:
            total = sum(new_weights.values())
            if abs(total - 1.0) > 0.01:  # Allow small floating point differences
                # Normalize weights
                normalized_weights = {k: v/total for k, v in new_weights.items()}
                self.weights = normalized_weights
                logging.info(f"Normalized and updated retrieval weights: {normalized_weights}")
            else:
                self.weights = new_weights.copy()
                logging.info(f"Updated retrieval weights: {new_weights}")
                
        except Exception as e:
            logging.error(f"Error updating weights: {e}")
    
    def get_memory_importance_score(self, memory_id: str, user_id: str) -> float:
        """Calculate importance score for a specific memory"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (m:Memory {id: $memory_id, user_id: $user_id})
                OPTIONAL MATCH (m)-[r:ASSOCIATED_WITH]-(other:Memory)
                WHERE other.user_id = $user_id
                WITH m, count(r) AS association_count
                RETURN 
                    (COALESCE(m.confidence, 0.5) * $conf_weight) +
                    ((COALESCE(m.access_count, 0) / 10.0) * $access_weight) +
                    ((association_count / 10.0) * $assoc_weight) AS importance_score
                """, 
                memory_id=memory_id, 
                user_id=user_id,
                conf_weight=config.IMPORTANCE_WEIGHTS['confidence'],
                access_weight=config.IMPORTANCE_WEIGHTS['access_frequency'],
                assoc_weight=config.IMPORTANCE_WEIGHTS['association_count'])
                
                record = result.single()
                if record:
                    return min(1.0, float(record['importance_score'] or 0.0))
                return 0.0
                
        except Exception as e:
            logging.error(f"Error calculating importance score: {e}")
            return 0.0