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

class TopicNode:
    """
    Represents a topic that contains related memory nodes.
    Topics form a hierarchical structure with subtopics.
    """
    
    def __init__(self, name: str, description: str = None, parent_topic_id: str = None, 
                 timestamp: datetime.datetime = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description or name
        self.parent_topic_id = parent_topic_id
        self.timestamp = timestamp or datetime.datetime.now()
        
    def __repr__(self):
        return f"TopicNode(id={self.id}, name='{self.name}', parent={self.parent_topic_id})"

class MemoryNode:
    """
    Represents a unit of memory with content and metadata.
    Now organized under topic nodes.
    """
    
    def __init__(self, content: str, confidence: float = 0.8, 
                 category: str = None, topic_id: str = None, timestamp: datetime.datetime = None):
        self.id = str(uuid.uuid4())
        self.content = content
        self.confidence = confidence
        self.category = category or self._detect_category(content)
        self.topic_id = topic_id
        self.timestamp = timestamp or datetime.datetime.now()
        
    def _detect_category(self, text: str) -> str:
        """Attempt to detect the category of the memory content."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['learn', 'study', 'understand', 'know', 'fact']):
            return 'learning'
        elif any(word in text_lower for word in ['feel', 'emotion', 'happy', 'sad', 'angry', 'excited']):
            return 'emotion'
        elif any(word in text_lower for word in ['conversation', 'chat', 'talk', 'discuss']):
            return 'conversation'
        elif any(word in text_lower for word in ['personal', 'about me', 'my', 'i am', 'i like']):
            return 'personal'
        elif any(word in text_lower for word in ['work', 'job', 'career', 'professional']):
            return 'professional'
        else:
            return 'general_knowledge'
    
    def __repr__(self):
        return f"MemoryNode(id={self.id}, content='{self.content[:50]}...', confidence={self.confidence})"
    
    def get_similarity_embedding(self) -> List[float]:
        """Get the embedding vector for this memory node - temporarily disabled"""
        # This would normally return the embedding vector for similarity calculations
        # For now, we'll use a simplified approach
        return []

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
        self.timestamp = timestamp or datetime.datetime.now()
        
    def decay(self):
        """Decay the relationship strength over time"""
        self.strength *= 0.95  # Decay by 5%
        
    def __repr__(self):
        return f"MemoryConnection({self.source_id} -> {self.target_id}, strength={self.strength})"

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
        """Generate embeddings using OpenAI API"""
        from utils import get_embedding_sync  # Import here to avoid circular imports
        return get_embedding_sync(text)
    
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
        
        with self.driver.session() as session:
            # Store memory node in Neo4j
            session.run(
                """
                MERGE (u:User {id: $user_id})
                CREATE (m:MemoryNode {
                    id: $memory_id,
                    content: $content,
                    confidence: $confidence,
                    category: $category,
                    timestamp: $timestamp,
                    embedding: $embedding
                })
                CREATE (u)-[:HAS_MEMORY]->(m)
                """,
                {
                    "user_id": user_id or "default_user",
                    "memory_id": memory_node.id,
                    "content": memory_node.content,
                    "confidence": memory_node.confidence,
                    "category": memory_node.category,
                    "timestamp": memory_node.timestamp,
                    "embedding": embedding
                }
            )
        
        # Create relationships with existing memories
        if user_id:
            self._create_memory_relationships(memory_node.id, embedding, user_id)
        
        return memory_node.id
        
    def _create_memory_relationships(self, new_memory_id: str, new_embedding: List[float], user_id: str):
        """Create semantic relationships between the new memory and existing memories"""
        with self.driver.session() as session:
            # Get existing memories for this user
            result = session.run(
                """
                MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:MemoryNode)
                WHERE m.id <> $new_memory_id AND m.embedding IS NOT NULL
                RETURN m.id AS id, m.embedding AS embedding
                LIMIT 20
                """,
                {"user_id": user_id, "new_memory_id": new_memory_id}
            )
            
            # Calculate similarities and create connections
            for record in result:
                stored_embedding = record["embedding"]
                if stored_embedding:
                    similarity = self._calculate_cosine_similarity(new_embedding, stored_embedding)
                    
                    # Create connection if similarity is above threshold
                    if similarity > 0.7:
                        session.run(
                            """
                            MATCH (m1:MemoryNode {id: $source_id})
                            MATCH (m2:MemoryNode {id: $target_id})
                            CREATE (m1)-[:SIMILAR_TO {
                                strength: $strength,
                                similarity: $similarity
                            }]->(m2)
                            """,
                            {
                                "source_id": new_memory_id,
                                "target_id": record["id"],
                                "strength": similarity,
                                "similarity": similarity
                            }
                        )
        
    def retrieve_memories(self, query: str, context: Optional[str] = None, depth: int = 5, user_id: Optional[str] = None) -> List[MemoryNode]:
        """Retrieve relevant memories based on semantic similarity"""
        if not user_id:
            return []
            
        with self.driver.session() as session:
            # Check for name-specific queries first
            name_keywords = ["name", "called", "Ryan", "I am", "my name is"]
            is_name_query = any(keyword.lower() in query.lower() for keyword in name_keywords)
            
            if is_name_query:
                # Prioritize name-related memories
                name_result = session.run(
                    """
                    MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:MemoryNode)
                    WHERE m.content CONTAINS 'Ryan' OR 
                          m.content CONTAINS 'name is' OR 
                          m.content CONTAINS 'I am' OR
                          m.content CONTAINS 'called'
                    RETURN m.id AS id, m.content AS content, m.confidence AS confidence,
                           m.category AS category, m.timestamp AS timestamp
                    ORDER BY m.timestamp DESC
                    LIMIT $depth
                    """,
                    {"user_id": user_id, "depth": depth}
                )
                
                memories = []
                for record in name_result:
                    memory_node = MemoryNode(
                        content=record["content"],
                        confidence=record["confidence"],
                        category=record["category"],
                        timestamp=record["timestamp"].to_native() if hasattr(record["timestamp"], 'to_native') else record["timestamp"]
                    )
                    memory_node.id = record["id"]
                    memories.append(memory_node)
                
                if memories:
                    return memories
            
            # Generate embedding for semantic search
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                return []
            
            # Get all memories for this user
            result = session.run(
                """
                MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:MemoryNode)
                RETURN m.id AS id, m.embedding AS embedding,
                       m.content AS content, m.confidence AS confidence,
                       m.category AS category, m.timestamp AS timestamp
                ORDER BY m.timestamp DESC
                """,
                {"user_id": user_id}
            )
            
            # Calculate similarities
            memories = []
            for record in result:
                stored_embedding = record["embedding"]
                if stored_embedding:
                    similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                    if similarity > 0.1:  # Low threshold to be inclusive
                        memory_node = MemoryNode(
                            content=record["content"],
                            confidence=record["confidence"],
                            category=record["category"],
                            timestamp=record["timestamp"].to_native() if hasattr(record["timestamp"], 'to_native') else record["timestamp"]
                        )
                        memory_node.id = record["id"]
                        memories.append((memory_node, similarity))
            
            # Sort by similarity and return top results
            memories.sort(key=lambda x: x[1], reverse=True)
            return [mem[0] for mem in memories[:depth]]
    
    def _calculate_relevance_score(self, memory_node: MemoryNode, query: str) -> float:
        """Calculate a relevance score based on semantic similarity"""
        # Simple keyword matching as fallback
        query_words = set(query.lower().split())
        content_words = set(memory_node.content.lower().split())
        
        if not query_words or not content_words:
            return 0.0
            
        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)
        
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        
        # Boost score based on confidence and recency
        confidence_boost = memory_node.confidence
        recency_boost = 1.0  # Could be based on timestamp
        
        return jaccard_similarity * confidence_boost * recency_boost
    
    def _contextual_filter(self, context: str, memory_nodes: List[MemoryNode]) -> List[MemoryNode]:
        """Filter memories based on conversational context"""
        if not context:
            return memory_nodes
        
        # Simple context filtering based on category matching
        context_lower = context.lower()
        relevant_categories = []
        
        if any(word in context_lower for word in ['personal', 'about', 'me', 'myself']):
            relevant_categories.append('personal')
        if any(word in context_lower for word in ['work', 'job', 'professional']):
            relevant_categories.append('professional')
        if any(word in context_lower for word in ['feel', 'emotion', 'mood']):
            relevant_categories.append('emotion')
        
        if not relevant_categories:
            return memory_nodes
        
        # Filter and sort by category relevance
        filtered_memories = []
        for memory in memory_nodes:
            if memory.category in relevant_categories:
                filtered_memories.append(memory)
        
        return filtered_memories or memory_nodes  # Return original if no matches
    
    def reinforce_memory(self, memory_id: str, reinforcement: float = 1.0) -> bool:
        """Increase the strength of a memory based on its usefulness"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (m:MemoryNode {id: $memory_id})
                    SET m.confidence = m.confidence + $reinforcement
                    RETURN m.confidence AS new_confidence
                    """,
                    {"memory_id": memory_id, "reinforcement": reinforcement}
                )
                
                record = result.single()
                if record:
                    new_confidence = min(record["new_confidence"], 1.0)  # Cap at 1.0
                    session.run(
                        "MATCH (m:MemoryNode {id: $memory_id}) SET m.confidence = $confidence",
                        {"memory_id": memory_id, "confidence": new_confidence}
                    )
                    return True
        except Exception as e:
            print(f"Error reinforcing memory: {e}")
        
        return False
    
    def decay_memories(self, force_decay=False):
        """Decay unused memories according to the forgetting algorithm"""
        current_time = datetime.datetime.now()
        
        with self.driver.session() as session:
            # Get all memories with their last access times
            result = session.run(
                """
                MATCH (m:MemoryNode)
                RETURN m.id AS id, m.confidence AS confidence, 
                       m.timestamp AS timestamp, m.category AS category
                """
            )
            
            for record in result:
                memory_time = record["timestamp"]
                if hasattr(memory_time, 'to_native'):
                    memory_time = memory_time.to_native()
                
                # Calculate time since creation
                time_diff = current_time - memory_time
                days_old = time_diff.days
                
                # Apply different decay rates based on category
                category = record["category"]
                if category == 'personal':
                    decay_rate = 0.01  # Very slow decay for personal info
                elif category == 'professional':
                    decay_rate = 0.02  # Slow decay for work-related
                elif category == 'emotion':
                    decay_rate = 0.05  # Faster decay for emotions
                else:
                    decay_rate = 0.03  # Standard decay rate
                
                # Calculate new confidence
                confidence = record["confidence"]
                new_confidence = confidence * (1 - decay_rate * days_old)
                new_confidence = max(new_confidence, 0.1)  # Minimum confidence
                
                # Update confidence in database
                session.run(
                    "MATCH (m:MemoryNode {id: $memory_id}) SET m.confidence = $confidence",
                    {"memory_id": record["id"], "confidence": new_confidence}
                )
        
        # Remove very low confidence memories
        self._forget_low_confidence_memories()
    
    def _forget_low_confidence_memories(self):
        """Remove memories that have decayed below a threshold"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (m:MemoryNode)
                WHERE m.confidence < 0.1
                DETACH DELETE m
                """
            )
    
    def _update_memory_confidence(self, memory_id: str, confidence: float) -> None:
        """Update the confidence level of a memory"""
        with self.driver.session() as session:
            session.run(
                "MATCH (m:MemoryNode {id: $memory_id}) SET m.confidence = $confidence",
                {"memory_id": memory_id, "confidence": confidence}
            )
    
    def learn_from_conversation(self, conversation: str) -> int:
        """Analyze and learn from a conversation"""
        # Split conversation into meaningful chunks
        sentences = conversation.split('.')
        memories_added = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Only process substantial sentences
                # Determine if this is worth remembering
                if any(keyword in sentence.lower() for keyword in 
                       ['i am', 'my name', 'i like', 'i work', 'i feel', 'remember', 'important']):
                    self.add_memory(sentence, confidence=0.8)
                    memories_added += 1
        
        return memories_added
    
    def detect_forgetfulness_patterns(self) -> Dict[str, float]:
        """Identify patterns in how different categories are forgotten"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MemoryNode)
                RETURN m.category AS category, COUNT(m) AS count, AVG(m.confidence) AS avg_confidence
                """
            )
            
            patterns = {}
            for record in result:
                category = record["category"]
                count = record["count"]
                avg_confidence = record["avg_confidence"]
                
                # Simple pattern: categories with lower average confidence are forgotten more
                def normal_decay_pattern(count):
                    return max(0.1, 1.0 - (count * 0.05))  # More memories = more decay
                
                expected_confidence = normal_decay_pattern(count)
                deviation = avg_confidence - expected_confidence
                
                patterns[category] = {
                    'count': count,
                    'avg_confidence': avg_confidence,
                    'expected_confidence': expected_confidence,
                    'deviation': deviation
                }
            
            return patterns
    
    def explain_forgetting(self, memory_id: str) -> str:
        """Provide reasoning for why a memory might be forgotten"""
        confidence = self._get_memory_confidence(memory_id)
        content = self._get_memory_content(memory_id)
        
        if confidence < 0.3:
            return f"Memory '{content[:30]}...' has low confidence ({confidence:.2f}) due to lack of recent reinforcement."
        elif confidence < 0.5:
            return f"Memory '{content[:30]}...' is moderately strong ({confidence:.2f}) but may decay without use."
        else:
            return f"Memory '{content[:30]}...' is well-established ({confidence:.2f}) and unlikely to be forgotten."
    
    def _get_memory_content(self, memory_id: str) -> str:
        """Helper method to get memory content from database"""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (m:MemoryNode {id: $memory_id}) RETURN m.content AS content",
                {"memory_id": memory_id}
            )
            record = result.single()
            return record["content"] if record else "Unknown memory"
    
    def _get_memory_confidence(self, memory_id: str) -> float:
        """Helper method to get memory confidence from database"""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (m:MemoryNode {id: $memory_id}) RETURN m.confidence AS confidence",
                {"memory_id": memory_id}
            )
            record = result.single()
            return record["confidence"] if record else 0.0
    
    def _train_embedding_model(self):
        """Placeholder for embedding model training based on usefulness feedback"""
        # This would involve training or fine-tuning the embedding model
        # based on which memories were found useful in conversations
        pass
    
    def get_memory_node(self, memory_id: str) -> Optional[MemoryNode]:
        """Retrieve a specific memory node from the database by ID"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MemoryNode {id: $memory_id})
                RETURN m.id AS id, m.content AS content, m.confidence AS confidence,
                       m.category AS category, m.timestamp AS timestamp
                """,
                {"memory_id": memory_id}
            )
            
            record = result.single()
            if record:
                memory_node = MemoryNode(
                    content=record["content"],
                    confidence=record["confidence"],
                    category=record["category"],
                    timestamp=record["timestamp"].to_native() if hasattr(record["timestamp"], 'to_native') else record["timestamp"]
                )
                memory_node.id = record["id"]
                return memory_node
            
            return None
    
    def forget_memory(self, memory_id: str) -> bool:
        """Permanently remove a memory from both Neo4j and ChromaDB vector store"""
        try:
            with self.driver.session() as session:
                # Remove the memory node and its relationships
                result = session.run(
                    """
                    MATCH (m:MemoryNode {id: $memory_id})
                    DETACH DELETE m
                    RETURN COUNT(m) AS deleted_count
                    """,
                    {"memory_id": memory_id}
                )
                
                record = result.single()
                return record["deleted_count"] > 0 if record else False
                
        except Exception as e:
            print(f"Error forgetting memory: {e}")
            return False
    
    def get_all_memory_nodes(self) -> List[MemoryNode]:
        """Retrieve all memory nodes from the database"""
        memories = []
        
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (m:MemoryNode)
                RETURN m.id AS id, m.content AS content, m.confidence AS confidence,
                       m.category AS category, m.timestamp AS timestamp
                ORDER BY m.timestamp DESC
                """
            )
            
            for record in result:
                memory_node = MemoryNode(
                    content=record["content"],
                    confidence=record["confidence"],
                    category=record["category"],
                    timestamp=record["timestamp"].to_native() if hasattr(record["timestamp"], 'to_native') else record["timestamp"]
                )
                memory_node.id = record["id"]
                memories.append(memory_node)
        
        return memories