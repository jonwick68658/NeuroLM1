import os
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
import config

class MemoryConsolidator:
    """Background memory consolidation and maintenance system"""
    
    def __init__(self, driver):
        self.driver = driver
        self.config = config.CONSOLIDATION_CONFIG
        
    def nightly_consolidation(self, user_id: str):
        """Run comprehensive nightly consolidation for a user"""
        try:
            logging.info(f"Starting nightly consolidation for user {user_id}")
            
            # Execute consolidation steps
            self.strengthen_important_memories(user_id)
            self.prune_inactive_memories(user_id)
            self.enhance_cross_links(user_id)
            self.adjust_confidence_levels(user_id)
            self.update_memory_statistics(user_id)
            
            logging.info(f"Completed nightly consolidation for user {user_id}")
            
        except Exception as e:
            logging.error(f"Error in nightly consolidation: {e}")
    
    def strengthen_important_memories(self, user_id: str):
        """Strengthen frequently accessed memories"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                WHERE m.access_count >= $threshold
                SET m.boost = COALESCE(m.boost, 1.0) * 
                    (1.0 + (0.1 * (1.0 - exp(-0.1 * m.access_count)))),
                    m.importance = CASE 
                        WHEN m.access_count > 10 THEN 'high'
                        WHEN m.access_count > 5 THEN 'medium'
                        ELSE 'normal'
                    END
                RETURN count(m) AS strengthened_count
                """, 
                user_id=user_id, 
                threshold=self.config['strengthen_threshold'])
                
                count = result.single()['strengthened_count']
                logging.info(f"Strengthened {count} important memories for user {user_id}")
                
        except Exception as e:
            logging.error(f"Error strengthening memories: {e}")
    
    def prune_inactive_memories(self, user_id: str):
        """Remove weak, inactive memories based on criteria"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config['prune_months'] * 30)
            
            with self.driver.session() as session:
                # First, identify candidates for pruning
                candidates = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                WHERE m.last_accessed < $cutoff_date
                AND COALESCE(m.access_count, 0) < $access_threshold
                AND COALESCE(m.confidence, 0.5) < $confidence_threshold
                AND NOT m.importance = 'high'
                RETURN count(m) AS prune_candidates
                """, 
                user_id=user_id,
                cutoff_date=cutoff_date,
                access_threshold=self.config['prune_access_threshold'],
                confidence_threshold=self.config['prune_confidence_threshold'])
                
                candidate_count = candidates.single()['prune_candidates']
                
                if candidate_count > 0:
                    # Actually prune the memories
                    result = session.run("""
                    MATCH (m:Memory {user_id: $user_id})
                    WHERE m.last_accessed < $cutoff_date
                    AND COALESCE(m.access_count, 0) < $access_threshold
                    AND COALESCE(m.confidence, 0.5) < $confidence_threshold
                    AND NOT m.importance = 'high'
                    DETACH DELETE m
                    RETURN count(m) AS pruned_count
                    """, 
                    user_id=user_id,
                    cutoff_date=cutoff_date,
                    access_threshold=self.config['prune_access_threshold'],
                    confidence_threshold=self.config['prune_confidence_threshold'])
                    
                    pruned_count = result.single()['pruned_count']
                    logging.info(f"Pruned {pruned_count} inactive memories for user {user_id}")
                else:
                    logging.info(f"No memories to prune for user {user_id}")
                    
        except Exception as e:
            logging.error(f"Error pruning memories: {e}")
    
    def enhance_cross_links(self, user_id: str):
        """Create associations between semantically similar memories"""
        try:
            with self.driver.session() as session:
                # Find and create new associations
                result = session.run("""
                MATCH (m1:Memory {user_id: $user_id}), (m2:Memory {user_id: $user_id})
                WHERE id(m1) < id(m2)
                AND NOT (m1)-[:ASSOCIATED_WITH]-(m2)
                AND m1.embedding IS NOT NULL AND m2.embedding IS NOT NULL
                WITH m1, m2, 
                     gds.similarity.cosine(m1.embedding, m2.embedding) AS similarity
                WHERE similarity > $threshold
                MERGE (m1)-[r:ASSOCIATED_WITH]->(m2)
                SET r.strength = similarity,
                    r.type = 'auto',
                    r.created = datetime()
                RETURN count(r) AS new_associations
                """, 
                user_id=user_id,
                threshold=self.config['association_threshold'])
                
                new_count = result.single()['new_associations']
                logging.info(f"Created {new_count} new associations for user {user_id}")
                
        except Exception as e:
            logging.error(f"Error enhancing cross-links: {e}")
    
    def adjust_confidence_levels(self, user_id: str):
        """Dynamically adjust memory confidence based on usage patterns"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                SET m.confidence = CASE
                    WHEN m.access_count IS NULL THEN 0.5
                    ELSE 0.7 * COALESCE(m.confidence, 0.5) + 
                         0.3 * (1.0 - 1.0 / (1.0 + 0.1 * m.access_count))
                END,
                m.last_confidence_update = datetime()
                RETURN count(m) AS updated_count
                """, user_id=user_id)
                
                count = result.single()['updated_count']
                logging.info(f"Updated confidence for {count} memories for user {user_id}")
                
        except Exception as e:
            logging.error(f"Error adjusting confidence levels: {e}")
    
    def update_memory_statistics(self, user_id: str):
        """Update user-level memory statistics"""
        try:
            with self.driver.session() as session:
                # Calculate and store user memory stats
                session.run("""
                MATCH (u:User {id: $user_id})
                OPTIONAL MATCH (u)-[:CREATED]->(m:Memory)
                OPTIONAL MATCH (m)-[r:ASSOCIATED_WITH]-(other:Memory)
                WITH u, 
                     count(DISTINCT m) AS total_memories,
                     count(DISTINCT r) AS total_associations,
                     avg(m.confidence) AS avg_confidence,
                     sum(m.access_count) AS total_accesses
                SET u.stats = {
                    total_memories: total_memories,
                    total_associations: total_associations,
                    avg_confidence: avg_confidence,
                    total_accesses: total_accesses,
                    last_updated: toString(datetime())
                }
                """, user_id=user_id)
                
                logging.info(f"Updated memory statistics for user {user_id}")
                
        except Exception as e:
            logging.error(f"Error updating memory statistics: {e}")
    
    def batch_process_users(self, batch_size: int = None):
        """Process consolidation for all users in batches"""
        try:
            batch_size = batch_size or config.PERFORMANCE_CONFIG['batch_size']
            
            with self.driver.session() as session:
                # Get all user IDs
                result = session.run("MATCH (u:User) RETURN u.id AS user_id")
                user_ids = [record['user_id'] for record in result]
                
                # Process in batches
                for i in range(0, len(user_ids), batch_size):
                    batch = user_ids[i:i + batch_size]
                    logging.info(f"Processing consolidation batch {i//batch_size + 1}: {len(batch)} users")
                    
                    for user_id in batch:
                        if user_id:  # Skip None values
                            self.nightly_consolidation(user_id)
                            
        except Exception as e:
            logging.error(f"Error in batch processing: {e}")
    
    def get_consolidation_report(self, user_id: str) -> Dict[str, Any]:
        """Generate a consolidation report for a user"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})
                OPTIONAL MATCH (u)-[:CREATED]->(m:Memory)
                OPTIONAL MATCH (m)-[r:ASSOCIATED_WITH]-(other:Memory)
                WITH u, m, r,
                     CASE WHEN m.importance = 'high' THEN 1 ELSE 0 END AS high_importance,
                     CASE WHEN COALESCE(m.access_count, 0) >= 5 THEN 1 ELSE 0 END AS frequently_accessed,
                     CASE WHEN r.strength > 0.7 THEN 1 ELSE 0 END AS strong_association
                RETURN {
                    total_memories: count(DISTINCT m),
                    high_importance_memories: sum(high_importance),
                    frequently_accessed: sum(frequently_accessed),
                    total_associations: count(DISTINCT r),
                    strong_associations: sum(strong_association),
                    avg_confidence: avg(m.confidence),
                    avg_access_count: avg(m.access_count),
                    last_consolidation: u.stats.last_updated
                } AS report
                """, user_id=user_id)
                
                record = result.single()
                if record:
                    return record['report']
                return {}
                
        except Exception as e:
            logging.error(f"Error generating consolidation report: {e}")
            return {}
    
    def emergency_cleanup(self, user_id: str):
        """Emergency cleanup for corrupted or problematic memories"""
        try:
            with self.driver.session() as session:
                # Remove memories with invalid embeddings
                result1 = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                WHERE m.embedding IS NULL OR size(m.embedding) <> 384
                DETACH DELETE m
                RETURN count(m) AS cleaned_invalid
                """, user_id=user_id)
                
                # Remove orphaned associations
                result2 = session.run("""
                MATCH ()-[r:ASSOCIATED_WITH]-()
                WHERE NOT EXISTS(startNode(r).user_id) OR NOT EXISTS(endNode(r).user_id)
                DELETE r
                RETURN count(r) AS cleaned_orphaned
                """)
                
                invalid_count = result1.single()['cleaned_invalid']
                orphaned_count = result2.single()['cleaned_orphaned']
                
                logging.info(f"Emergency cleanup: removed {invalid_count} invalid memories and {orphaned_count} orphaned associations")
                
        except Exception as e:
            logging.error(f"Error in emergency cleanup: {e}")