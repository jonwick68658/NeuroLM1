"""
Background RIAI Evaluation Service - PostgreSQL Version
Processes unscored memories for R(t) evaluation without blocking user responses
"""

import asyncio
import hashlib
import time
import os
import psycopg2
from typing import List, Dict, Optional
from model_service import ModelService

class BackgroundRIAIService:
    """Service for background R(t) evaluation with batching and caching"""
    
    def __init__(self):
        self.model_service = ModelService()
        self.is_running = False
        self.batch_size = 20
        self.process_interval = 1800  # 30 minutes
        self.db_url = os.getenv("DATABASE_URL")
        
    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(self.db_url)
        
    def generate_response_hash(self, content: str) -> str:
        """Generate hash for response content to enable caching"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_cached_score(self, response_hash: str) -> Optional[float]:
        """Check if we have a cached R(t) score for this response"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r_t_score FROM memory_quality_cache 
                WHERE response_hash = %s
            """, (response_hash,))
            
            result = cursor.fetchone()
            cursor.close()
            
            return result[0] if result else None
                
        except Exception as e:
            print(f"Error checking cache: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    async def store_cached_score(self, response_hash: str, r_t_score: float):
        """Store R(t) score in cache for future use"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO memory_quality_cache (response_hash, r_t_score)
                VALUES (%s, %s)
                ON CONFLICT (response_hash) 
                DO UPDATE SET r_t_score = EXCLUDED.r_t_score
            """, (response_hash, r_t_score))
            
            conn.commit()
            cursor.close()
                
        except Exception as e:
            print(f"Error storing cache: {e}")
        finally:
            if conn:
                conn.close()
    
    async def get_unscored_memories(self, limit: int = 20) -> List[Dict]:
        """Get memories that need R(t) evaluation"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, content, user_id, created_at
                FROM intelligent_memories
                WHERE message_type = 'assistant'
                AND r_t_score IS NULL
                AND content IS NOT NULL
                ORDER BY created_at ASC
                LIMIT %s
            """, (limit,))
            
            memories = []
            for record in cursor.fetchall():
                memories.append({
                    'memory_id': record[0],
                    'content': record[1],
                    'user_id': record[2],
                    'timestamp': record[3]
                })
            
            cursor.close()
            return memories
                
        except Exception as e:
            print(f"Error getting unscored memories: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    async def evaluate_batch(self, memories: List[Dict]) -> List[Dict]:
        """Evaluate a batch of memories for R(t) scores"""
        evaluation_results = []
        
        for memory in memories:
            try:
                content = memory['content']
                response_hash = self.generate_response_hash(content)
                
                # Check cache first
                cached_score = await self.get_cached_score(response_hash)
                if cached_score is not None:
                    print(f"Using cached R(t) score: {cached_score}")
                    evaluation_results.append({
                        'memory_id': memory['memory_id'],
                        'user_id': memory['user_id'],
                        'r_t_score': cached_score,
                        'cached': True
                    })
                    continue
                
                # Evaluate using Mistral model
                messages = [
                    {"role": "system", "content": "You are an AI response quality evaluator. Rate the quality of AI responses on a scale of 1-10, where 1 is poor and 10 is excellent. Consider accuracy, helpfulness, clarity, and completeness. Respond with just the numerical score."},
                    {"role": "user", "content": f"Rate this AI response: {content}"}
                ]
                
                # Use Mistral-Small for evaluation
                response_text = await self.model_service.chat_completion(
                    messages=messages,
                    model="mistralai/mistral-small-3.2-24b-instruct"
                )
                
                # Extract numerical score with improved parsing
                score_text = response_text.strip()
                try:
                    # Try direct float conversion first
                    r_t_score = float(score_text)
                except ValueError:
                    # Try parsing from various formats
                    import re
                    # Look for patterns like "Score: 9", "**Score: 9**", "9/10", etc.
                    score_patterns = [
                        r'\*\*Score:\s*(\d+(?:\.\d+)?)\*\*',  # **Score: 9**
                        r'Score:\s*(\d+(?:\.\d+)?)',          # Score: 9
                        r'(\d+(?:\.\d+)?)/10',                # 9/10
                        r'(\d+(?:\.\d+)?)$',                  # Just number at end
                        r'(\d+(?:\.\d+)?)',                   # Any number
                    ]
                    
                    r_t_score = None
                    for pattern in score_patterns:
                        match = re.search(pattern, score_text)
                        if match:
                            try:
                                r_t_score = float(match.group(1))
                                break
                            except ValueError:
                                continue
                    
                    if r_t_score is None:
                        print(f"Could not parse R(t) score: {score_text}")
                        continue
                
                # Clamp to valid range
                r_t_score = max(1.0, min(10.0, r_t_score))
                
                # Store in cache
                await self.store_cached_score(response_hash, r_t_score)
                
                evaluation_results.append({
                    'memory_id': memory['memory_id'],
                    'user_id': memory['user_id'],
                    'r_t_score': r_t_score,
                    'cached': False
                })
                
                print(f"R(t) evaluation: {r_t_score}/10 for memory {memory['memory_id'][:8]}...")
                    
            except Exception as e:
                print(f"Error evaluating memory {memory['memory_id']}: {e}")
                continue
        
        return evaluation_results
    
    async def update_memory_scores(self, evaluation_results: List[Dict]):
        """Update memories with R(t) scores and calculate final quality scores"""
        for result in evaluation_results:
            conn = None
            try:
                memory_id = result['memory_id']
                user_id = result['user_id']
                r_t_score = result['r_t_score']
                
                # Update R(t) score in PostgreSQL
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                # Update R(t) score
                cursor.execute("""
                    UPDATE intelligent_memories 
                    SET r_t_score = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (r_t_score, memory_id))
                
                # Get current H(t) score to calculate final quality score
                cursor.execute("""
                    SELECT h_t_score FROM intelligent_memories WHERE id = %s
                """, (memory_id,))
                
                h_t_result = cursor.fetchone()
                h_t_score = h_t_result[0] if h_t_result and h_t_result[0] is not None else None
                
                # Calculate final quality score using f(R(t), H(t))
                final_quality_score = self.calculate_final_quality_score(r_t_score, h_t_score)
                
                # Update final quality score
                cursor.execute("""
                    UPDATE intelligent_memories 
                    SET final_quality_score = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (final_quality_score, memory_id))
                
                conn.commit()
                cursor.close()
                
                print(f"Updated memory {str(memory_id)[:8]}... with R(t)={r_t_score}, final={final_quality_score}")
                
            except Exception as e:
                print(f"Error updating memory scores: {e}")
            finally:
                if conn:
                    conn.close()
    
    def calculate_final_quality_score(self, r_t_score: Optional[float], h_t_score: Optional[float]) -> Optional[float]:
        """Calculate final quality score using f(R(t), H(t)) intelligence refinement function"""
        if r_t_score is None:
            return None
        
        # Base score from R(t) evaluation
        base_score = r_t_score
        
        # Apply human feedback with 1.5x weighting if available
        if h_t_score is not None:
            # Weighted average with human feedback having 1.5x weight
            total_weight = 1.0 + 1.5  # R(t) weight + H(t) weight
            final_score = (base_score * 1.0 + h_t_score * 1.5) / total_weight
        else:
            final_score = base_score
        
        # Ensure score is in valid range
        return max(1.0, min(10.0, final_score))
    
    async def process_batch(self) -> Dict[str, int]:
        """Process a batch of unscored memories"""
        try:
            # Get unscored memories
            memories = await self.get_unscored_memories(self.batch_size)
            
            if not memories:
                print("No memories to evaluate")
                return {'processed': 0, 'cached': 0, 'evaluated': 0}
            
            print(f"Processing {len(memories)} memories for R(t) evaluation")
            
            # Evaluate batch
            evaluation_results = await self.evaluate_batch(memories)
            
            if not evaluation_results:
                print("No successful evaluations")
                return {'processed': 0, 'cached': 0, 'evaluated': 0}
            
            # Update memory scores
            await self.update_memory_scores(evaluation_results)
            
            # Calculate statistics
            cached_count = sum(1 for r in evaluation_results if r['cached'])
            evaluated_count = len(evaluation_results) - cached_count
            
            return {
                'processed': len(evaluation_results),
                'cached': cached_count,
                'evaluated': evaluated_count
            }
            
        except Exception as e:
            print(f"Error in batch processing: {e}")
            return {'processed': 0, 'cached': 0, 'evaluated': 0}
    
    async def start_background_service(self):
        """Start the background R(t) evaluation service"""
        self.is_running = True
        print("Background RIAI service started")
        
        # Initial delay to allow server startup
        print("Waiting 45 seconds before first batch processing...")
        await asyncio.sleep(45)
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Process batch
                stats = await self.process_batch()
                
                processing_time = time.time() - start_time
                
                print(f"Batch processed in {processing_time:.2f}s: "
                      f"{stats['processed']} total, {stats['cached']} cached, "
                      f"{stats['evaluated']} evaluated")
                
                # Wait for next cycle
                await asyncio.sleep(self.process_interval)
                
            except Exception as e:
                print(f"Error in background service: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_background_service(self):
        """Stop the background R(t) evaluation service"""
        self.is_running = False
        print("Background RIAI service stopped")
    
    def close(self):
        """Close connections"""
        self.stop_background_service()

# Global instance for background service
background_riai_service = None

async def start_background_riai():
    """Start the background RIAI service"""
    global background_riai_service
    if background_riai_service is None:
        background_riai_service = BackgroundRIAIService()
        await background_riai_service.start_background_service()

async def stop_background_riai():
    """Stop the background RIAI service"""
    global background_riai_service
    if background_riai_service:
        background_riai_service.stop_background_service()
        background_riai_service = None

async def process_riai_batch():
    """Process a single batch of R(t) evaluations"""
    global background_riai_service
    if background_riai_service is None:
        background_riai_service = BackgroundRIAIService()
    
    return await background_riai_service.process_batch()
