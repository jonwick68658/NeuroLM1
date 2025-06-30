"""
Relationship Analyzer for Phase 2: Topic Clustering and Cross-Topic Connections
Analyzes relationships between memories, topics, and conversations
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from neo4j import GraphDatabase
from model_service import ModelService
import json
import re

class RelationshipAnalyzer:
    """Analyzes and creates relationships between memories and topics"""
    
    def __init__(self):
        # Neo4j connection (reuse existing configuration)
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j") 
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        self.model_service = ModelService()
        
        # Configuration
        self.similarity_threshold = 0.7  # For topic clustering
        self.min_cluster_size = 3       # Minimum memories for a topic cluster
    
    def _setup_relationship_indexes(self):
        """Create indexes for relationship analysis"""
        try:
            with self.driver.session() as session:
                # Create index for topic clusters
                session.run("""
                    CREATE INDEX topic_cluster_index IF NOT EXISTS
                    FOR (t:TopicCluster) ON (t.user_id, t.cluster_name)
                """)
                
                # Create index for memory relationships
                session.run("""
                    CREATE INDEX memory_relationship_index IF NOT EXISTS
                    FOR ()-[r:RELATES_TO]-() ON (r.strength, r.created_at)
                """)
                
                print("✅ Relationship indexes created successfully")
        except Exception as e:
            print(f"❌ Relationship index setup failed: {e}")
            raise e
    
    async def extract_topics_from_content(self, content: str) -> List[str]:
        """Extract semantic topics from memory content using AI"""
        try:
            system_prompt = """You are a topic extraction system. Extract 1-3 main topics from the given text.

Rules:
1. Return only concrete, specific topics (not vague terms)
2. Use single words or short phrases (max 3 words)
3. Focus on the main subject matter
4. Return as a JSON array of strings
5. If no clear topics, return empty array

Examples:
Input: "I love cooking Italian pasta dishes"
Output: ["cooking", "italian food", "pasta"]

Input: "The weather is nice today"
Output: ["weather"]"""

            user_prompt = f"Extract topics from this text:\n\n{content}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.model_service.chat_completion(
                messages=messages,
                model="openai/gpt-4o-mini"
            )
            
            # Parse JSON response
            try:
                topics = json.loads(response.strip())
                if isinstance(topics, list):
                    return [str(topic).lower().strip() for topic in topics if topic]
            except json.JSONDecodeError:
                # Fallback: extract from response text
                topics = re.findall(r'"([^"]+)"', response)
                return [topic.lower().strip() for topic in topics if len(topic) > 2]
            
            return []
            
        except Exception as e:
            print(f"Error extracting topics: {e}")
            return []
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings for topic clustering"""
        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding generation error: {e}")
            return []
    
    async def analyze_memory_relationships(self, user_id: str, limit: int = 10) -> Dict[str, any]:
        """Analyze relationships between recent memories"""
        try:
            with self.driver.session() as session:
                # Get recent memories for analysis (reduced scope for initial testing)
                result = session.run("""
                    MATCH (m:IntelligentMemory)
                    WHERE m.user_id = $user_id
                    RETURN m.id as id, m.content as content, m.conversation_id as conversation_id,
                           m.timestamp as timestamp
                    ORDER BY m.timestamp DESC
                    LIMIT $limit
                """, user_id=user_id, limit=limit)
                
                memories = []
                for record in result:
                    memories.append({
                        'id': record['id'],
                        'content': record['content'],
                        'conversation_id': record['conversation_id'],
                        'timestamp': record['timestamp']
                    })
                
                if len(memories) < self.min_cluster_size:
                    return {"status": "insufficient_data", "memories_analyzed": len(memories)}
                
                print(f"Analyzing relationships for {len(memories)} memories")
                
                # Extract topics for each memory
                memory_topics = {}
                for memory in memories:
                    topics = await self.extract_topics_from_content(memory['content'])
                    if topics:
                        memory_topics[memory['id']] = topics
                
                # Find topic clusters
                topic_clusters = self._cluster_by_topics(memory_topics)
                
                # Create relationship nodes
                relationships_created = 0
                for cluster_name, memory_ids in topic_clusters.items():
                    if len(memory_ids) >= self.min_cluster_size:
                        cluster_id = await self._create_topic_cluster(
                            user_id, cluster_name, memory_ids
                        )
                        if cluster_id:
                            relationships_created += 1
                
                return {
                    "status": "completed",
                    "memories_analyzed": len(memories),
                    "topic_clusters_created": relationships_created,
                    "topics_found": len(topic_clusters)
                }
                
        except Exception as e:
            print(f"Error analyzing memory relationships: {e}")
            return {"status": "error", "error": str(e)}
    
    def _cluster_by_topics(self, memory_topics: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Cluster memories by shared topics"""
        topic_to_memories = {}
        
        # Group memories by topics
        for memory_id, topics in memory_topics.items():
            for topic in topics:
                if topic not in topic_to_memories:
                    topic_to_memories[topic] = []
                topic_to_memories[topic].append(memory_id)
        
        # Filter out topics with too few memories
        clusters = {}
        for topic, memory_ids in topic_to_memories.items():
            if len(memory_ids) >= self.min_cluster_size:
                clusters[topic] = memory_ids
        
        return clusters
    
    async def _create_topic_cluster(self, user_id: str, cluster_name: str, 
                                   memory_ids: List[str]) -> Optional[str]:
        """Create a topic cluster node and relationships"""
        try:
            with self.driver.session() as session:
                # Create topic cluster node
                result = session.run("""
                    CREATE (tc:TopicCluster {
                        id: randomUUID(),
                        user_id: $user_id,
                        cluster_name: $cluster_name,
                        memory_count: $memory_count,
                        created_at: datetime()
                    })
                    RETURN tc.id as cluster_id
                """, 
                user_id=user_id,
                cluster_name=cluster_name,
                memory_count=len(memory_ids)
                )
                
                cluster_record = result.single()
                if not cluster_record:
                    return None
                
                cluster_id = cluster_record['cluster_id']
                
                # Create relationships to memories
                for memory_id in memory_ids:
                    session.run("""
                        MATCH (tc:TopicCluster {id: $cluster_id})
                        MATCH (m:IntelligentMemory {id: $memory_id})
                        CREATE (tc)-[:CONTAINS_MEMORY {
                            strength: 1.0,
                            created_at: datetime()
                        }]->(m)
                    """, cluster_id=cluster_id, memory_id=memory_id)
                
                print(f"✅ Created topic cluster '{cluster_name}' with {len(memory_ids)} memories")
                return cluster_id
                
        except Exception as e:
            print(f"Error creating topic cluster: {e}")
            return None
    
    async def find_cross_topic_relationships(self, user_id: str) -> Dict[str, any]:
        """Find relationships between different topic clusters"""
        try:
            with self.driver.session() as session:
                # Get existing topic clusters
                result = session.run("""
                    MATCH (tc:TopicCluster)
                    WHERE tc.user_id = $user_id
                    RETURN tc.id as cluster_id, tc.cluster_name as cluster_name,
                           tc.memory_count as memory_count
                    ORDER BY tc.created_at DESC
                """, user_id=user_id)
                
                clusters = []
                for record in result:
                    clusters.append({
                        'id': record['cluster_id'],
                        'name': record['cluster_name'],
                        'memory_count': record['memory_count']
                    })
                
                if len(clusters) < 2:
                    return {"status": "insufficient_clusters", "clusters_found": len(clusters)}
                
                # Analyze relationships between clusters using AI
                relationships_found = await self._analyze_cluster_relationships(user_id, clusters)
                
                return {
                    "status": "completed",
                    "clusters_analyzed": len(clusters),
                    "relationships_found": relationships_found
                }
                
        except Exception as e:
            print(f"Error finding cross-topic relationships: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _analyze_cluster_relationships(self, user_id: str, clusters: List[Dict]) -> int:
        """Analyze relationships between topic clusters using AI"""
        try:
            relationships_created = 0
            
            # Compare each pair of clusters
            for i, cluster1 in enumerate(clusters):
                for j, cluster2 in enumerate(clusters[i+1:], i+1):
                    
                    # Get sample memories from each cluster
                    samples1 = await self._get_cluster_memory_samples(cluster1['id'])
                    samples2 = await self._get_cluster_memory_samples(cluster2['id'])
                    
                    if samples1 and samples2:
                        # Analyze relationship using AI
                        relationship_strength = await self._calculate_relationship_strength(
                            cluster1['name'], samples1, cluster2['name'], samples2
                        )
                        
                        if relationship_strength > 0.6:  # Threshold for significant relationship
                            await self._create_cluster_relationship(
                                cluster1['id'], cluster2['id'], relationship_strength
                            )
                            relationships_created += 1
            
            return relationships_created
            
        except Exception as e:
            print(f"Error analyzing cluster relationships: {e}")
            return 0
    
    async def _get_cluster_memory_samples(self, cluster_id: str, limit: int = 3) -> List[str]:
        """Get sample memory contents from a cluster"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (tc:TopicCluster {id: $cluster_id})-[:CONTAINS_MEMORY]->(m:IntelligentMemory)
                    RETURN m.content as content
                    ORDER BY m.timestamp DESC
                    LIMIT $limit
                """, cluster_id=cluster_id, limit=limit)
                
                return [record['content'] for record in result]
        except Exception as e:
            print(f"Error getting cluster samples: {e}")
            return []
    
    async def _calculate_relationship_strength(self, topic1: str, samples1: List[str], 
                                              topic2: str, samples2: List[str]) -> float:
        """Calculate relationship strength between two topic clusters"""
        try:
            system_prompt = """You are a relationship analyzer. Determine how strongly two topics are related based on sample content.

Rate the relationship strength from 0.0 to 1.0:
- 0.0-0.3: Unrelated or very weak connection
- 0.4-0.6: Some connection exists
- 0.7-0.9: Strong relationship
- 1.0: Very closely related

Consider:
- Conceptual overlap
- Contextual connections
- User's personal patterns
- Complementary topics

Return only a single number between 0.0 and 1.0."""

            samples1_text = "\n".join(samples1[:3])
            samples2_text = "\n".join(samples2[:3])
            
            user_prompt = f"""Topic 1: {topic1}
Sample content:
{samples1_text}

Topic 2: {topic2}
Sample content:
{samples2_text}

Rate relationship strength (0.0-1.0):"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.model_service.chat_completion(
                messages=messages,
                model="openai/gpt-4o-mini"
            )
            
            # Extract numeric score
            try:
                score = float(response.strip())
                return max(0.0, min(1.0, score))  # Clamp to valid range
            except ValueError:
                # Fallback: parse from response
                import re
                numbers = re.findall(r'0\.\d+|1\.0|0', response)
                if numbers:
                    return float(numbers[0])
                return 0.0
                
        except Exception as e:
            print(f"Error calculating relationship strength: {e}")
            return 0.0
    
    async def _create_cluster_relationship(self, cluster1_id: str, cluster2_id: str, 
                                          strength: float) -> bool:
        """Create relationship between two topic clusters"""
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (tc1:TopicCluster {id: $cluster1_id})
                    MATCH (tc2:TopicCluster {id: $cluster2_id})
                    CREATE (tc1)-[:RELATES_TO {
                        strength: $strength,
                        created_at: datetime()
                    }]->(tc2)
                """, cluster1_id=cluster1_id, cluster2_id=cluster2_id, strength=strength)
                
                print(f"✅ Created relationship between clusters (strength: {strength:.2f})")
                return True
                
        except Exception as e:
            print(f"Error creating cluster relationship: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        self.driver.close()

# Initialize the relationship analyzer
relationship_analyzer = RelationshipAnalyzer()