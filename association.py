import os
import logging
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4
from neo4j import GraphDatabase
import numpy as np
import config

class AssociationEngine:
    """Advanced association discovery and management system"""
    
    def __init__(self, driver):
        self.driver = driver
        self.decay_rate = config.ASSOCIATION_CONFIG['decay_rate']
        self.max_hops = config.ASSOCIATION_CONFIG['max_hops']
        self.context_threshold = config.ASSOCIATION_CONFIG['context_threshold']
        self.auto_strength = config.ASSOCIATION_CONFIG['auto_association_strength']
        
    def update_relationship_strength(self, user_id: str = None):
        """Apply temporal decay to all associations and remove weak ones"""
        try:
            with self.driver.session() as session:
                # Apply temporal decay to all associations
                decay_query = """
                MATCH ()-[r:ASSOCIATED_WITH]-()
                """
                if user_id:
                    decay_query += """
                    WHERE startNode(r).user_id = $user_id AND endNode(r).user_id = $user_id
                    """
                decay_query += """
                SET r.strength = r.strength * (1 - $decay)
                RETURN count(r) AS updated_count
                """
                
                result = session.run(decay_query, decay=self.decay_rate, user_id=user_id)
                updated_count = result.single()['updated_count']
                
                # Remove weak associations
                removal_query = """
                MATCH ()-[r:ASSOCIATED_WITH]-()
                WHERE r.strength < $threshold
                """
                if user_id:
                    removal_query += """
                    AND startNode(r).user_id = $user_id AND endNode(r).user_id = $user_id
                    """
                removal_query += """
                DELETE r
                RETURN count(r) AS removed_count
                """
                
                result = session.run(removal_query, 
                                   threshold=config.CONSOLIDATION_CONFIG['weak_association_threshold'],
                                   user_id=user_id)
                removed_count = result.single()['removed_count']
                
                logging.info(f"Updated {updated_count} associations, removed {removed_count} weak ones")
                
        except Exception as e:
            logging.error(f"Error updating relationship strength: {e}")
    
    def discover_multi_hop_associations(self, memory_id: str, user_id: str, hops: int = None) -> List[Dict[str, Any]]:
        """Discover indirect associations through multiple hops"""
        try:
            hops = hops or self.max_hops
            
            with self.driver.session() as session:
                result = session.run("""
                MATCH path = (start:Memory {id: $memory_id, user_id: $user_id})
                            -[:ASSOCIATED_WITH*1..$hops]-(related:Memory {user_id: $user_id})
                WHERE start <> related
                UNWIND relationships(path) AS rel
                WITH related, 
                     avg(rel.strength) AS path_strength,
                     length(path) AS path_length,
                     min(rel.strength) AS weakest_link
                WHERE path_strength > 0.4 AND weakest_link > 0.3
                RETURN related {
                    .id, .content, .timestamp, .confidence, .access_count
                } AS memory,
                path_strength,
                path_length,
                weakest_link
                ORDER BY path_strength DESC, path_length ASC
                LIMIT 10
                """, memory_id=memory_id, user_id=user_id, hops=hops)
                
                associations = []
                for record in result:
                    associations.append({
                        'memory': record['memory'],
                        'path_strength': float(record['path_strength']),
                        'path_length': record['path_length'],
                        'weakest_link': float(record['weakest_link'])
                    })
                
                logging.info(f"Found {len(associations)} multi-hop associations for memory {memory_id}")
                return associations
                
        except Exception as e:
            logging.error(f"Error discovering multi-hop associations: {e}")
            return []
    
    def contextual_clustering(self, context_embedding: List[float], user_id: str, cluster_size: int = 20) -> str:
        """Create contextual clusters of related memories"""
        try:
            context_id = str(uuid4())
            
            with self.driver.session() as session:
                # Find memories similar to the context
                result = session.run("""
                CALL db.index.vector.queryNodes('memory_embeddings', $cluster_size, $embedding)
                YIELD node AS memory
                WHERE memory.user_id = $user_id
                WITH collect(memory) AS cluster
                
                // Create associations within the cluster
                UNWIND cluster AS m1
                UNWIND cluster AS m2
                WHERE id(m1) < id(m2)
                WITH m1, m2, 
                     gds.similarity.cosine(m1.embedding, m2.embedding) AS similarity
                WHERE similarity > $threshold
                MERGE (m1)-[r:CONTEXT_ASSOC]->(m2)
                SET r.strength = similarity,
                    r.context_id = $context_id,
                    r.created = datetime(),
                    r.type = 'contextual'
                RETURN count(r) AS associations_created
                """, 
                cluster_size=cluster_size,
                embedding=context_embedding,
                user_id=user_id,
                threshold=self.context_threshold,
                context_id=context_id)
                
                count = result.single()['associations_created']
                logging.info(f"Created {count} contextual associations in cluster {context_id}")
                
                return context_id
                
        except Exception as e:
            logging.error(f"Error in contextual clustering: {e}")
            return ""
    
    def strengthen_co_accessed_memories(self, user_id: str):
        """Strengthen associations between memories accessed together"""
        try:
            with self.driver.session() as session:
                # Find memories that were accessed close in time
                result = session.run("""
                MATCH (m1:Memory {user_id: $user_id}), (m2:Memory {user_id: $user_id})
                WHERE id(m1) < id(m2)
                AND abs(duration.between(m1.last_accessed, m2.last_accessed).seconds) < 300
                AND m1.last_accessed IS NOT NULL AND m2.last_accessed IS NOT NULL
                OPTIONAL MATCH (m1)-[existing:ASSOCIATED_WITH]-(m2)
                WITH m1, m2, existing,
                     CASE WHEN existing IS NULL THEN 0.6 ELSE existing.strength END AS current_strength
                MERGE (m1)-[r:ASSOCIATED_WITH]-(m2)
                SET r.strength = CASE 
                    WHEN existing IS NULL THEN 0.6
                    ELSE least(1.0, current_strength + 0.1)
                END,
                r.co_access_boost = TRUE,
                r.last_strengthened = datetime()
                RETURN count(r) AS strengthened_count
                """, user_id=user_id)
                
                count = result.single()['strengthened_count']
                logging.info(f"Strengthened {count} co-accessed memory associations")
                
        except Exception as e:
            logging.error(f"Error strengthening co-accessed memories: {e}")
    
    def detect_memory_clusters(self, user_id: str, min_cluster_size: int = 3) -> List[Dict[str, Any]]:
        """Detect and return memory clusters based on associations"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                OPTIONAL MATCH (m)-[r:ASSOCIATED_WITH]-(connected:Memory {user_id: $user_id})
                WHERE r.strength > 0.5
                WITH m, collect(DISTINCT connected) AS cluster_members
                WHERE size(cluster_members) >= $min_size
                RETURN m {.id, .content, .timestamp} AS center,
                       [member IN cluster_members | member {.id, .content, .timestamp}] AS members,
                       size(cluster_members) AS cluster_size
                ORDER BY cluster_size DESC
                LIMIT 10
                """, user_id=user_id, min_size=min_cluster_size)
                
                clusters = []
                for record in result:
                    clusters.append({
                        'center': record['center'],
                        'members': record['members'],
                        'size': record['cluster_size']
                    })
                
                logging.info(f"Found {len(clusters)} memory clusters for user {user_id}")
                return clusters
                
        except Exception as e:
            logging.error(f"Error detecting memory clusters: {e}")
            return []
    
    def create_topic_associations(self, user_id: str):
        """Create associations between memories sharing topics"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (m1:Memory {user_id: $user_id})-[:ABOUT]->(topic:Topic)<-[:ABOUT]-(m2:Memory {user_id: $user_id})
                WHERE id(m1) < id(m2)
                AND NOT (m1)-[:ASSOCIATED_WITH]-(m2)
                WITH m1, m2, count(topic) AS shared_topics
                WHERE shared_topics >= 1
                MERGE (m1)-[r:ASSOCIATED_WITH]-(m2)
                SET r.strength = 0.5 + (shared_topics * 0.1),
                    r.type = 'topic_based',
                    r.shared_topics = shared_topics,
                    r.created = datetime()
                RETURN count(r) AS topic_associations_created
                """, user_id=user_id)
                
                count = result.single()['topic_associations_created']
                logging.info(f"Created {count} topic-based associations for user {user_id}")
                
        except Exception as e:
            logging.error(f"Error creating topic associations: {e}")
    
    def get_association_network_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics about the association network"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (m:Memory {user_id: $user_id})
                OPTIONAL MATCH (m)-[r:ASSOCIATED_WITH]-(other:Memory {user_id: $user_id})
                WITH m, r, other,
                     CASE WHEN r.strength > 0.7 THEN 1 ELSE 0 END AS strong_connection,
                     CASE WHEN r.type = 'auto' THEN 1 ELSE 0 END AS auto_connection,
                     CASE WHEN r.type = 'topic_based' THEN 1 ELSE 0 END AS topic_connection
                RETURN {
                    total_memories: count(DISTINCT m),
                    total_associations: count(DISTINCT r),
                    strong_associations: sum(strong_connection),
                    auto_associations: sum(auto_connection),
                    topic_associations: sum(topic_connection),
                    avg_association_strength: avg(r.strength),
                    max_connections_per_memory: max(size((m)-[:ASSOCIATED_WITH]-())),
                    connectivity_ratio: toFloat(count(DISTINCT r)) / count(DISTINCT m)
                } AS stats
                """, user_id=user_id)
                
                record = result.single()
                if record:
                    return record['stats']
                return {}
                
        except Exception as e:
            logging.error(f"Error getting association network stats: {e}")
            return {}
    
    def find_association_paths(self, source_id: str, target_id: str, user_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Find paths between two specific memories"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH path = shortestPath(
                    (source:Memory {id: $source_id, user_id: $user_id})
                    -[:ASSOCIATED_WITH*...$max_depth]-
                    (target:Memory {id: $target_id, user_id: $user_id})
                )
                UNWIND relationships(path) AS rel
                RETURN nodes(path) AS path_nodes,
                       relationships(path) AS path_rels,
                       length(path) AS path_length,
                       reduce(total = 1.0, r IN relationships(path) | total * r.strength) AS path_strength
                ORDER BY path_length ASC, path_strength DESC
                LIMIT 5
                """, source_id=source_id, target_id=target_id, user_id=user_id, max_depth=max_depth)
                
                paths = []
                for record in result:
                    paths.append({
                        'nodes': [dict(node) for node in record['path_nodes']],
                        'relationships': [dict(rel) for rel in record['path_rels']],
                        'length': record['path_length'],
                        'strength': float(record['path_strength'])
                    })
                
                return paths
                
        except Exception as e:
            logging.error(f"Error finding association paths: {e}")
            return []
    
    def optimize_associations(self, user_id: str):
        """Optimize the association network by removing redundant weak links"""
        try:
            with self.driver.session() as session:
                # Remove redundant associations where stronger paths exist
                result = session.run("""
                MATCH (m1:Memory {user_id: $user_id})-[direct:ASSOCIATED_WITH]-(m2:Memory {user_id: $user_id})
                WHERE direct.strength < 0.6
                WITH m1, m2, direct,
                     shortestPath((m1)-[:ASSOCIATED_WITH*2..4]-(m2)) AS indirect_path
                WHERE indirect_path IS NOT NULL
                UNWIND relationships(indirect_path) AS indirect_rel
                WITH m1, m2, direct, 
                     reduce(strength = 1.0, r IN relationships(indirect_path) | strength * r.strength) AS indirect_strength
                WHERE indirect_strength > direct.strength
                DELETE direct
                RETURN count(direct) AS optimized_count
                """, user_id=user_id)
                
                count = result.single()['optimized_count']
                logging.info(f"Optimized {count} redundant associations for user {user_id}")
                
        except Exception as e:
            logging.error(f"Error optimizing associations: {e}")