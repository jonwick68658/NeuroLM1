"""
Background RIAI Evaluation Service
Processes unscored memories for R(t) evaluation without blocking user responses
"""

import asyncio
import hashlib
import time
from typing import List, Dict, Optional
from intelligent_memory import IntelligentMemorySystem
from model_service import ModelService

class BackgroundRIAIService:
    """Service for background R(t) evaluation with batching and caching"""
    
    def __init__(self):
        self.memory_system = IntelligentMemorySystem()
        self.model_service = ModelService()
        self.is_running = False
        self.batch_size = 20
        self.process_interval = 1800  # 30 minutes
        
    def generate_response_hash(self, content: str) -> str:
        """Generate hash for response content to enable caching"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_cached_score(self, response_hash: str) -> Optional[float]:
        """Check if we have a cached R(t) score for this response"""
        try:
            with self.memory_system.driver.session() as session:
                result = session.run("""
                    MATCH (c:ResponseCache {response_hash: $response_hash})
                    RETURN c.r_t_score AS score
                """, {'response_hash': response_hash})
                
                record = result.single()
                return record['score'] if record else None
                
        except Exception as e:
            print(f"Error checking cache: {e}")
            return None
    
    async def store_cached_score(self, response_hash: str, r_t_score: float):
        """Store R(t) score in cache for future use"""
        try:
            with self.memory_system.driver.session() as session:
                session.run("""
                    MERGE (c:ResponseCache {response_hash: $response_hash})
                    SET c.r_t_score = $r_t_score,
                        c.cached_at = datetime()
                """, {
                    'response_hash': response_hash,
                    'r_t_score': r_t_score
                })
                
        except Exception as e:
            print(f"Error storing cache: {e}")
    
    async def get_unscored_memories(self, limit: int = 20) -> List[Dict]:
        """Get memories that need R(t) evaluation"""
        try:
            with self.memory_system.driver.session() as session:
                result = session.run("""
                    MATCH (m:IntelligentMemory)
                    WHERE m.message_type = 'assistant'
                    AND m.quality_score IS NULL
                    AND m.content IS NOT NULL
                    RETURN m.id AS memory_id,
                           m.content AS content,
                           m.user_id AS user_id,
                           m.timestamp AS timestamp
                    ORDER BY m.timestamp ASC
                    LIMIT $limit
                """, {'limit': limit})
                
                memories = []
                for record in result:
                    memories.append({
                        'memory_id': record['memory_id'],
                        'content': record['content'],
                        'user_id': record['user_id'],
                        'timestamp': record['timestamp']
                    })
                
                return memories
                
        except Exception as e:
            print(f"Error getting unscored memories: {e}")
            return []
    
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
                
                # Evaluate using DeepSeek model
                messages = [
                    {"role": "system", "content": "You are an AI response quality evaluator. Rate the quality of AI responses on a scale of 1-10, where 1 is poor and 10 is excellent. Consider accuracy, helpfulness, clarity, and completeness. Respond with just the numerical score."},
                    {"role": "user", "content": f"Rate this AI response: {content}"}
                ]
                
                # Use DeepSeek-R1-Distill for evaluation
                response_text = await self.model_service.chat_completion(
                    messages=messages,
                    model="deepseek/deepseek-r1-distill-qwen-7b"
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
            try:
                memory_id = result['memory_id']
                user_id = result['user_id']
                r_t_score = result['r_t_score']
                
                # Update R(t) score
                await self.memory_system.update_memory_quality_score(memory_id, r_t_score)
                
                # Calculate final quality score using f(R(t), H(t))
                await self.memory_system.update_final_quality_score(memory_id, user_id)
                
                print(f"Updated memory {memory_id[:8]}... with R(t)={r_t_score}")
                
            except Exception as e:
                print(f"Error updating memory scores: {e}")
    
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
        self.memory_system.close()

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