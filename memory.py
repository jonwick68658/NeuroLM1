import datetime
import uuid
import json
import math
import random
from typing import List, Dict, Set, Tuple, Optional
import os
from neo4j import GraphDatabase


# Note: sentence_transformers removed to resolve dependency conflicts
# We'll use OpenAI embeddings through utils.py instead

class MemoryNode:
    """
    Represents a unit of memory with content and metadata.
    """

    def __init__(self, content: str, confidence: float = 0.8, 
                 category: str = None, timestamp: datetime.datetime = None):
        self.id = str(uuid.uuid4())
        self.content = content
        self.confidence = confidence
        self.category = category or self._detect_category(content)
        self.timestamp = timestamp or datetime.datetime.now()
        self.connections = set()  # Will store only IDs for now
        self.reinforcement = 0.0  # How much this memory has been reinforced
        self.decay_rate = 0.0005  # Daily decay rate
        
    def _detect_category(self, text: str) -> str:
        """Attempt to detect the category of the memory content."""
        # Basic rule-based categorization
        if "person" in text or "name" in text or "meet" in text:
            return "social_organizational"
        elif "buy" in text or "sell" in text or "price" in text or "cost" in text:
            return "economic"
        elif "error" in text.lower() or "exception" in text.lower():
            return "technical_issues"
        elif any(doc_word in text.lower() for doc_word in ["read", "document", "file", "pdf"]):
            return "document_related"
        else:
            return "general_knowledge"

    def __repr__(self):
        return f"MemoryNode(id={self.id}, content={self.content[:50]}..., confidence={self.confidence})"

    def get_similarity_embedding(self) -> List[float]:
        """Get the embedding vector for this memory node - temporarily disabled"""
        # return EMBEDDING_MODEL.encode(self.content).tolist()
        return [0.0] * 384  # Return dummy embedding vector

class MemoryConnection:
    """
    Represents a relationship between memory nodes.
    """
    
    def __init__(self, source_id: str, target_id: str, strength: float = 1.0,
                 relationship_type: str = "SIMILAR_TO", timestamp: datetime.datetime = None):
        self.id = str(uuid.uuid4())
        self.source_id = source_id
        self.target_id = target_id
        self.strength = strength
        self.relationship_type = relationship_type
        self.timestamp = timestamp if timestamp else datetime.datetime.now()
        
    def decay(self):
        """Decay the relationship strength over time"""
        self.strength = max(0.1, self.strength * 0.995)  # Slight decay but keep some minimum strength
        
    def __repr__(self):
        return (f"MemoryConnection(id={self.id}, source={self.source_id}, "
                f"target={self.target_id}, strength={self.strength})")

class MemorySystem:
    """
    The main memory system that interacts with Neo4j and manages memory operations.
    """
    
    def __init__(self):
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        self.conversation_history = []
        self.past_queries = {}
        self.usefulness_history = []
        self._create_schema()
        
    def _create_schema(self):
        """Create the database schema with vector support"""
        with self.driver.session() as session:
            # Create constraints and indexes
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:MemoryNode) REQUIRE m.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Connection) REQUIRE c.id IS UNIQUE")
            
            # Create index for vector similarity search
            session.run("CREATE INDEX IF NOT EXISTS FOR (m:MemoryNode) ON (m.category)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (m:MemoryNode) ON (m.confidence)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.username)")
            
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI API and store in Neo4j"""
        try:
            from utils import generate_embedding
            return generate_embedding(text)
        except Exception as e:
            print(f"Warning: Could not generate embedding: {e}")
            # Return a default zero vector if embedding generation fails
            return [0.0] * 1536  # OpenAI text-embedding-3-small dimension
    
    def _calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        import math
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(a * a for a in embedding2))
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
            
        return dot_product / (magnitude1 * magnitude2)
        
    def _cypher_query(self, tx, query: str, parameters: Optional[Dict] = None):
        """Helper method for executing Cypher queries"""
        return tx.run(query, parameters or {})
        
    def add_memory(self, content: str, confidence: float = 0.8, user_id: Optional[str] = None) -> str:
        """Add a new memory to the system and return its ID"""
        # Create memory node
        memory_node = MemoryNode(content, confidence)
        
        # Generate embedding for semantic search
        embedding = self._generate_embedding(content)
        
        # Save to Neo4j with embedding and user relationship
        with self.driver.session() as session:
            if user_id:
                # Create memory and link to user
                session.run(
                    """
                    MATCH (u:User {id: $user_id})
                    CREATE (m:MemoryNode {
                        id: $id,
                        content: $content,
                        confidence: $confidence,
                        category: $category,
                        timestamp: datetime($timestamp),
                        embedding: $embedding
                    })
                    CREATE (u)-[:HAS_MEMORY]->(m)
                    """,
                    {
                        "user_id": user_id,
                        "id": memory_node.id,
                        "content": memory_node.content,
                        "confidence": memory_node.confidence,
                        "category": memory_node.category,
                        "timestamp": memory_node.timestamp.isoformat(),
                        "embedding": embedding
                    }
                )
            else:
                # Create memory without user link (backward compatibility)
                session.run(
                    """
                    CREATE (m:MemoryNode {
                        id: $id,
                        content: $content,
                        confidence: $confidence,
                        category: $category,
                        timestamp: datetime($timestamp),
                        embedding: $embedding
                    })
                    """,
                    {
                        "id": memory_node.id,
                        "content": memory_node.content,
                        "confidence": memory_node.confidence,
                        "category": memory_node.category,
                        "timestamp": memory_node.timestamp.isoformat(),
                        "embedding": embedding
                    }
                )
        
        # Create semantic relationships with existing memories for the same user
        if user_id:
            self._create_memory_relationships(memory_node.id, embedding, user_id)
        
        return memory_node.id
    
    def _create_memory_relationships(self, new_memory_id: str, new_embedding: List[float], user_id: str):
        """Create semantic relationships between the new memory and existing memories"""
        similarity_threshold = 0.7  # Only create relationships for highly similar memories
        
        with self.driver.session() as session:
            # Find similar memories for the same user
            result = session.run(
                """
                MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:MemoryNode)
                WHERE m.id <> $new_memory_id AND m.embedding IS NOT NULL
                RETURN m.id AS id, m.embedding AS embedding
                """,
                {"user_id": user_id, "new_memory_id": new_memory_id}
            )
            
            # Calculate similarities and create relationships
            for record in result:
                existing_embedding = record["embedding"]
                similarity = self._calculate_cosine_similarity(new_embedding, existing_embedding)
                
                if similarity >= similarity_threshold:
                    # Create bidirectional RELATES_TO relationship
                    session.run(
                        """
                        MATCH (m1:MemoryNode {id: $memory1_id})
                        MATCH (m2:MemoryNode {id: $memory2_id})
                        MERGE (m1)-[:RELATES_TO {similarity: $similarity, created_at: datetime()}]->(m2)
                        MERGE (m2)-[:RELATES_TO {similarity: $similarity, created_at: datetime()}]->(m1)
                        """,
                        {
                            "memory1_id": new_memory_id,
                            "memory2_id": record["id"],
                            "similarity": similarity
                        }
                    )
        
    def retrieve_memories(self, query: str, context: Optional[str] = None, depth: int = 5, user_id: Optional[str] = None) -> List[MemoryNode]:
        """Retrieve relevant memories based on query and context using Neo4j vector search"""
        # Generate embedding for the query
        query_embedding = self._generate_embedding(query)
        
        # Find similar memories using Neo4j vector similarity
        with self.driver.session() as session:
            if user_id:
                # Get ALL user memories for similarity calculation
                result = session.run(
                    """
                    MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:MemoryNode)
                    WHERE m.embedding IS NOT NULL
                    RETURN m.id AS id, m.embedding AS embedding,
                           m.content AS content, m.confidence AS confidence,
                           m.timestamp AS timestamp
                    ORDER BY m.timestamp DESC
                    """,
                    {"user_id": user_id}
                )
            else:
                # Return empty list if no user_id provided to enforce user isolation
                return []
            
            # Calculate similarity scores with recency boost
            candidates = []
            for record in result:
                stored_embedding = record["embedding"]
                if stored_embedding:
                    similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                    
                    # Add recency boost - more recent memories get higher scores
                    timestamp = record["timestamp"]
                    if timestamp:
                        from datetime import datetime
                        try:
                            # Convert Neo4j datetime to Python datetime for comparison
                            memory_time = timestamp.to_native() if hasattr(timestamp, 'to_native') else timestamp
                            time_diff_hours = (datetime.now() - memory_time).total_seconds() / 3600
                            # Boost recent memories: 10% boost for memories less than 1 hour old
                            recency_boost = max(0, 0.1 * (1 - min(time_diff_hours / 24, 1)))
                            similarity = min(1.0, similarity + recency_boost)
                        except:
                            pass  # If timestamp parsing fails, use original similarity
                    
                    candidates.append((record["id"], similarity))
            
            # Sort by similarity and get top results
            candidates.sort(key=lambda x: x[1], reverse=True)
            top_ids = [candidate[0] for candidate in candidates[:depth]]
            
            # Retrieve full memory nodes
            memories = []
            for memory_id in top_ids:
                memory_node = self.get_memory_node(memory_id)
                if memory_node:
                    memories.append(memory_node)
                    
            return memories
        
    def _calculate_relevance_score(self, memory_node: MemoryNode, query: str) -> float:
        """Calculate a relevance score based on semantic similarity"""
        # In a complete implementation, we'd use the actual embedding vectors
        # Since we don't have the full implementation, we'll simulate this
        return random.uniform(0.5, 1.0)
        
    def _contextual_filter(self, context: str, memory_nodes: List[MemoryNode]) -> List[MemoryNode]:
        """Filter memories based on conversational context"""
        # Simple implementation that returns all nodes but weights recent ones
        return memory_nodes
        
    def reinforce_memory(self, memory_id: str, reinforcement: float = 1.0) -> bool:
        """Increase the strength of a memory based on its usefulness"""
        # Log the reinforcement
        self.usefulness_history.append({
            "memory_id": memory_id,
            "reinforcement": reinforcement,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # If we have enough data, train the embedding model
        if len(self.usefulness_history) % 10 == 0:
            self._train_embedding_model()
            
        with self.driver.session() as session:
            session.write_transaction(
                self._cypher_query,
                """
                MATCH (m:MemoryNode {id: $memory_id})
                SET m.reinforcement = COALESCE(m.reinforcement, 0) + $reinforcement,
                    m.confidence = m.confidence + $reinforcement * 0.01
                RETURN m.confidence AS new_confidence
                """,
                {
                    "memory_id": memory_id,
                    "reinforcement": reinforcement
                }
            )
            
        return self._get_memory_confidence(memory_id)
        
    def decay_memories(self, force_decay=False):
        """Decay unused memories according to the forgetting algorithm"""
        # Only decay under certain conditions
        if not force_decay and datetime.datetime.now().hour != 3:  # Only at 3AM
            return
            
        # 1. Calculate daily decay rate based on system load (for simulation purposes)
        decay_rate = self.decay_rate * random.uniform(0.8, 1.2)
        
        # 2. Retrieve memories with low confidence
        with self.driver.session() as session:
            result = session.read_transaction(
                self._cypher_query,
                """
                MATCH (m:MemoryNode)
                RETURN m.id AS id, m.confidence AS confidence
                ORDER BY m.confidence ASC  # Lowest confidence first
                LIMIT 100  # Sample a subset for decay
                """
            )
            
            for record in result:
                memory_id = record["id"]
                current_confidence = record["confidence"]
                new_confidence = max(0.1, current_confidence - decay_rate)
                
                if new_confidence != current_confidence:
                    self._update_memory_confidence(memory_id, new_confidence)
                    
        # 3. Remove memories with very low confidence (simulated version)
        self._forget_low_confidence_memories()
        
    def _forget_low_confidence_memories(self):
        """Remove memories that have decayed below a threshold"""
        # In a real system, we'd remove these entirely
        # In this simulation, we mark them as decayed
        with self.driver.session() as session:
            session.write_transaction(
                self._cypher_query,
                """
                MATCH (m:MemoryNode)
                WHERE m.confidence < 0.1
                SET m.decayed_at = datetime()
                RETURN COUNT(m) AS memories_forget
                """
            )
            
    def _update_memory_confidence(self, memory_id: str, confidence: float) -> None:
        """Update the confidence level of a memory"""
        with self.driver.session() as session:
            session.write_transaction(
                self._cypher_query,
                """
                MATCH (m:MemoryNode {id: $memory_id})
                SET m.confidence = $confidence
                RETURN m.confidence AS updated_confidence
                """,
                {
                    "memory_id": memory_id,
                    "confidence": confidence
                }
            )
            
    def learn_from_conversation(self, conversation: str) -> int:
        """Analyze and learn from a conversation"""
        # Placeholder for full implementation
        # This would extract key points, categorize them, and create new memories
        # For now, just count sentences as "memorization events"
        sentences = conversation.split(". ")  # Simple sentence splitter
        new_memories_count = len(sentences)
        
        # Create simplified memory entries for conversation structure
        self.add_memory(f"Conversation about '{conversation[:50]}...'")
        
        return new_memories_count
        
    def detect_forgetfulness_patterns(self) -> Dict[str, float]:
        """Identify patterns in how different categories are forgotten"""
        # In a complete implementation, this would analyze forgetting rates
        # by category
        
        categories = {}
        with self.driver.session() as session:
            result = session.read_transaction(
                self._cypher_query,
                """
                MATCH (m:MemoryNode)
                RETURN m.category AS category, COUNT(m) AS count
                GROUP BY m.category
                ORDER BY count DESC
                """
            )
            
        for record in result:
            category = record["category"]
            count = record["count"]
            if category:
                categories[category] = count
                
        # Simple simulation of decay patterns
        def normal_decay_pattern(count):
            return math.log(max(count, 1)) * 0.5
            
        return {k: normal_decay_pattern(v) for k, v in categories.items()}
        
    def explain_forgetting(self, memory_id: str) -> str:
        """Provide reasoning for why a memory might be forgotten"""
        with self.driver.session() as session:
            result = session.read_transaction(
                self._cypher_query,
                """
                MATCH (m:MemoryNode {id: $memory_id})
                RETURN m.confidence AS confidence, 
                       m.category AS category,
                       date(m.timestamp) AS creation_date,
                       date() AS current_date
                """,
                {
                    "memory_id": memory_id
                }
            )
            
            record = result.single()
            if not record:
                return "No memory found with that ID"
                
            confidence = record["confidence"]
            category = record["category"]
            creation_date = record["creation_date"].split("T")[0]
            current_date = record["current_date"].split("T")[0]
            
            days_old = (datetime.datetime.strptime(current_date, "%Y-%m-%d") - 
                        datetime.datetime.strptime(creation_date, "%Y-%m-%d")).days
            
            # Different reasons for forgetting based on category
            reasons = {
                "social_organizational": "This memory pertains to social or organizational matters. "
                    "As such, it has higher importance and is protected from decay.",
                "economic": "Economic information changes frequently, so this memory is prioritized "
                    "for updating and reinforcement.",
                "technical_issues": "Technical issues often require immediate attention. "
                    "This memory remains easily accessible unless deprecated.",
                "document_related": "Documents provide valuable information. This memory has been "
                    "protected or accelerated decay based on relevance.",
                "general_knowledge": ""
            }
            
            explanation = (f"This memory about '{memory_id[:10]}...' was "
                          f"created on {creation_date} and is {days_old} days old.\n\n"
                          f"It currently has a confidence score of {confidence:.1f}.\n\n")
                    
            if category in reasons:
                explanation += reasons[category]
                
            # Add decay-based explanation
            decay_factor = days_old * 0.001
            if confidence < 0.3:
                decay_threshold = 30
                explanation += (f"\nIts low confidence means it has been experiencing accelerated "
                               f"decay, especially since its last reinforcement. Memories like "
                               f"these typically fade after {decay_threshold} days of inactivity.")
            else:
                explanation += (f"\nThis memory has been reinforced and maintained at a higher "
                               f"confidence level of {confidence:.1f}, so it has been preserved "
                               "and is unlikely to decay soon.")
                
            return explanation[:1000] + "..." if len(explanation) > 1000 else explanation
            
    def _get_memory_content(self, memory_id: str) -> str:
        """Helper method to get memory content from database"""
        with self.driver.session() as session:
            result = session.read_transaction(
                self._cypher_query,
                """
                MATCH (m:MemoryNode {id: $memory_id})
                RETURN m.content AS content
                """,
                {"memory_id": memory_id}
            )
            record = result.single()
            return record["content"] if record else ""
            
    def _get_memory_confidence(self, memory_id: str) -> float:
        """Helper method to get memory confidence from database"""
        with self.driver.session() as session:
            result = session.read_transaction(
                self._cypher_query,
                """
                MATCH (m:MemoryNode {id: $memory_id})
                RETURN m.confidence AS confidence
                """,
                {"memory_id": memory_id}
            )
            record = result.single()
            return record["confidence"] if record else 0.0
            
    def _train_embedding_model(self):
        """Placeholder for embedding model training based on usefulness feedback"""
        # In a complete implementation, this would retrain the embedding model
        # based on which memories were marked as useful
        pass
        
    def get_memory_node(self, memory_id: str) -> Optional[MemoryNode]:
        """Retrieve a specific memory node from the database by ID"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MemoryNode {id: $memory_id})
                RETURN m AS memory_node
                """,
                {
                    "memory_id": memory_id
                }
            )
            
            record = result.single()
            if record:
                memory_node_data = {
                    "id": record["memory_node"].get("id"),
                    "content": record["memory_node"].get("content"),
                    "confidence": record["memory_node"].get("confidence", 0.5),
                    "category": record["memory_node"].get("category"),
                    "timestamp": record["memory_node"].get("timestamp"),
                    "connections": record["memory_node"].get("connections", [])
                }
                
                return MemoryNode(
                    content=memory_node_data["content"],
                    confidence=memory_node_data["confidence"],
                    category=memory_node_data["category"],
                    timestamp=memory_node_data["timestamp"] if memory_node_data["timestamp"] else None
                )
        return None
        
    def forget_memory(self, memory_id: str) -> bool:
        """Permanently remove a memory from both Neo4j and ChromaDB vector store"""
        try:
            # Remove from Neo4j
            with self.driver.session() as session:
                session.run(
                    """
                    MATCH (m:MemoryNode {id: $memory_id})
                    DETACH DELETE m
                    RETURN count(m) AS deleted
                    """,
                    {
                        "memory_id": memory_id
                    }
                )
                
            # Neo4j deletion is complete (embedding stored in same node)
                
            return True
        except Exception as e:
            print(f"Error forgetting memory {memory_id}: {str(e)}")
            return False
            
    def get_all_memory_nodes(self) -> List[MemoryNode]:
        """Retrieve all memory nodes from the database"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MemoryNode)
                RETURN m.id AS id
                """
            )
            
            all_memory_nodes = []
            for record in result:
                memory_node = self.get_memory_node(record["id"])
                if memory_node:
                    all_memory_nodes.append(memory_node)
                    
            return all_memory_nodes