#!/usr/bin/env python3
"""
Neural Memory System for NeuroLM
Hierarchical topic-based memory that mimics human cognitive organization
"""

import os
import uuid
from neo4j import GraphDatabase
from utils import generate_embedding
from typing import List, Dict, Any, Optional
import json
import openai

class NeuralMemorySystem:
    """Hierarchical topic-based memory system"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
        self.openai_client = openai.OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )

        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema and constraints"""
        with self.driver.session() as session:
            # Create constraints
            session.run("CREATE CONSTRAINT user_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            session.run("CREATE CONSTRAINT topic_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE")
            session.run("CREATE CONSTRAINT memory_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE")
            
            # Create vector indexes for semantic search
            try:
                session.run("CREATE VECTOR INDEX memory_embeddings IF NOT EXISTS FOR (m:Memory) ON (m.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}")
                session.run("CREATE VECTOR INDEX topic_embeddings IF NOT EXISTS FOR (t:Topic) ON (t.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}")
            except:
                pass  # Indexes might already exist
    
    def create_user(self, user_id: str, username: str = None) -> bool:
        """Create a user node"""
        try:
            with self.driver.session() as session:
                session.run("""
                MERGE (u:User {id: $user_id})
                SET u.username = $username, u.created_at = datetime()
                """, user_id=user_id, username=username or user_id)
                return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def extract_topics(self, content: str) -> list:
        """Extract multiple topics from conversation content using Gemini 2.0 Flash"""
        try:
            # Try Gemini 2.0 Flash first
            response = self.openai_client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[
                    {"role": "system", "content": "Extract 1-3 main topics from this conversation. Avoid creating separate topics for related concepts (e.g., 'Fitness' and 'Health' for workout discussions should be 'Health & Fitness'). Format: 'Primary: TopicName, Secondary: TopicName, Tertiary: TopicName' (only include what's relevant). Examples: 'Primary: Health & Fitness' or 'Primary: Cooking, Secondary: Nutrition'. Use 1-4 words per topic, consolidate related concepts."},
                    {"role": "user", "content": content}
                ],
                temperature=0.2,
                max_tokens=40
            )
            
            response_text = response.choices[0].message.content.strip()
            topics = []
            
            # Parse the response to extract topics
            if response_text:
                parts = response_text.split(',')
                for part in parts:
                    if ':' in part:
                        topic = part.split(':', 1)[1].strip()
                        if topic and len(topics) < 3:
                            topics.append(topic)
            
            return topics if topics else ["General Discussion"]
            
        except Exception as e:
            print(f"Gemini topic extraction failed, trying fallback: {e}")
            # Fallback to GPT-4o Mini
            try:
                response = self.openai_client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Extract 1-3 main topics from this conversation. Avoid creating separate topics for related concepts (e.g., 'Fitness' and 'Health' for workout discussions should be 'Health & Fitness'). Format: 'Primary: TopicName, Secondary: TopicName, Tertiary: TopicName' (only include what's relevant). Use 1-4 words per topic, consolidate related concepts."},
                        {"role": "user", "content": content}
                    ],
                    temperature=0.2,
                    max_tokens=40
                )
                
                response_text = response.choices[0].message.content.strip()
                topics = []
                
                if response_text:
                    parts = response_text.split(',')
                    for part in parts:
                        if ':' in part:
                            topic = part.split(':', 1)[1].strip()
                            if topic and len(topics) < 3:
                                topics.append(topic)
                
                return topics if topics else ["General Discussion"]
                
            except Exception as fallback_error:
                print(f"All topic extraction failed: {fallback_error}")
                return ["General Discussion"]
    
    def find_or_create_topic(self, user_id: str, topic_name: str, content: str) -> str:
        """Find existing topic or create new one with enhanced collision detection"""
        try:
            topic_embedding = generate_embedding(f"{topic_name} {content}")
            topic_id = str(uuid.uuid4())
            
            with self.driver.session() as session:
                # If no embedding available, use name-based matching only
                if topic_embedding is None:
                    result = session.run("""
                    MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)
                    WHERE toLower(t.name) = toLower($topic_name)
                    RETURN t.id as topic_id
                    LIMIT 1
                    """, user_id=user_id, topic_name=topic_name)
                    
                    existing = result.single()
                    if existing:
                        return existing['topic_id']
                    
                    # Create topic without embedding
                    session.run("""
                    MATCH (u:User {id: $user_id})
                    CREATE (t:Topic {
                        id: $topic_id,
                        name: $topic_name,
                        created_at: datetime(),
                        memory_count: 0
                    })
                    CREATE (u)-[:HAS_TOPIC]->(t)
                    """, user_id=user_id, topic_id=topic_id, topic_name=topic_name)
                    
                    print(f"Created new topic: {topic_name} (no embedding)")
                    return topic_id
                
                # Use embedding-based similarity check
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)
                WHERE t.embedding IS NOT NULL
                WITH t, 
                     vector.similarity.cosine(t.embedding, $topic_embedding) AS similarity,
                     CASE 
                         WHEN toLower(t.name) CONTAINS toLower($topic_name) OR toLower($topic_name) CONTAINS toLower(t.name) 
                         THEN 0.2 
                         ELSE 0.0 
                     END AS name_bonus
                WHERE similarity + name_bonus > 0.75
                RETURN t.id as topic_id, t.name as name, similarity + name_bonus as final_score
                ORDER BY final_score DESC
                LIMIT 1
                """, user_id=user_id, topic_embedding=topic_embedding, topic_name=topic_name)
                
                existing = result.single()
                if existing:
                    print(f"Found existing topic: {existing['name']} (score: {existing['final_score']:.3f})")
                    return existing['topic_id']
                
                # Create new topic with embedding
                session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (t:Topic {
                    id: $topic_id,
                    name: $topic_name,
                    embedding: $topic_embedding,
                    created_at: datetime(),
                    memory_count: 0
                })
                CREATE (u)-[:HAS_TOPIC]->(t)
                """, user_id=user_id, topic_id=topic_id, topic_name=topic_name, topic_embedding=topic_embedding)
                
                print(f"Created new topic: {topic_name}")
                return topic_id
                
        except Exception as e:
            print(f"Error finding/creating topic: {e}")
            return None
    
    def store_conversation(self, user_id: str, role: str, content: str) -> Optional[str]:
        """Store conversation in hierarchical topic structure"""
        try:
            # Extract multiple topics from content
            topics = self.extract_topics(content)
            
            # Generate embedding for content
            content_embedding = generate_embedding(content)
            memory_id = str(uuid.uuid4())
            
            # Create memory node (with or without embedding)
            with self.driver.session() as session:
                if content_embedding is not None:
                    session.run("""
                    CREATE (m:Memory {
                        id: $memory_id,
                        role: $role,
                        content: $content,
                        embedding: $content_embedding,
                        created_at: datetime(),
                        access_count: 0,
                        relevance_score: 1.0
                    })
                    """, memory_id=memory_id, role=role, content=content, content_embedding=content_embedding)
                else:
                    session.run("""
                    CREATE (m:Memory {
                        id: $memory_id,
                        role: $role,
                        content: $content,
                        created_at: datetime(),
                        access_count: 0,
                        relevance_score: 1.0
                    })
                    """, memory_id=memory_id, role=role, content=content)
            
            # Connect memory to all relevant topics
            for topic_name in topics:
                topic_id = self.find_or_create_topic(user_id, topic_name, content)
                if topic_id:
                    with self.driver.session() as session:
                        session.run("""
                        MATCH (t:Topic {id: $topic_id}), (m:Memory {id: $memory_id})
                        CREATE (t)-[:CONTAINS_MEMORY]->(m)
                        SET t.memory_count = t.memory_count + 1,
                            t.last_updated = datetime()
                        """, topic_id=topic_id, memory_id=memory_id)
                
            # Create cross-topic links if content references other topics  
            self._create_cross_topic_links(memory_id, content, user_id)
            
            return memory_id
                
        except Exception as e:
            print(f"Error storing conversation: {e}")
            return None
    
    def _create_cross_topic_links(self, memory_id: str, content: str, user_id: str):
        """Create links between memories across different topics"""
        try:
            content_embedding = generate_embedding(content)
            
            # Skip cross-topic linking if no embedding available
            if content_embedding is None:
                return
            
            with self.driver.session() as session:
                
                # Find semantically similar memories in other topics
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                WHERE m.id <> $memory_id AND m.embedding IS NOT NULL
                WITH m, vector.similarity.cosine(m.embedding, $content_embedding) AS similarity
                WHERE similarity > 0.75
                RETURN m.id as related_memory_id, similarity
                ORDER BY similarity DESC
                LIMIT 3
                """, user_id=user_id, memory_id=memory_id, content_embedding=content_embedding)
                
                # Create relationships to related memories
                for record in result:
                    session.run("""
                    MATCH (m1:Memory {id: $memory_id}), (m2:Memory {id: $related_memory_id})
                    CREATE (m1)-[:RELATES_TO {strength: $similarity}]->(m2)
                    """, memory_id=memory_id, related_memory_id=record['related_memory_id'], similarity=record['similarity'])
                    
        except Exception as e:
            print(f"Error creating cross-topic links: {e}")
    
    def retrieve_context(self, user_id: str, query: str, limit: int = 5) -> str:
        """Retrieve contextual memories using topic hierarchy"""
        try:
            query_embedding = generate_embedding(query)
            context_parts = []
            
            with self.driver.session() as session:
                # If no query embedding available, use text-based search
                if query_embedding is None:
                    result = session.run("""
                    MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                    WHERE m.content CONTAINS $query OR t.name CONTAINS $query
                    RETURN t.name as topic, m.role as role, m.content as content, 1.0 as combined_score
                    ORDER BY m.created_at DESC
                    LIMIT $limit
                    """, user_id=user_id, query=query, limit=limit)
                else:
                    # Find relevant topics first using embeddings
                    result = session.run("""
                    MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)
                    WHERE t.embedding IS NOT NULL
                    WITH t, vector.similarity.cosine(t.embedding, $query_embedding) AS topic_similarity
                    WHERE topic_similarity > 0.6
                    
                    // Get memories from relevant topics
                    MATCH (t)-[:CONTAINS_MEMORY]->(m:Memory)
                    WHERE m.embedding IS NOT NULL
                    WITH t, m, topic_similarity, vector.similarity.cosine(m.embedding, $query_embedding) AS memory_similarity
                    
                    // Combined scoring: topic relevance + memory relevance
                    WITH t, m, (topic_similarity * 0.3 + memory_similarity * 0.7) AS combined_score
                    WHERE combined_score > 0.6
                    
                    RETURN t.name as topic, m.role as role, m.content as content, combined_score
                    ORDER BY combined_score DESC
                    LIMIT $limit
                    """, user_id=user_id, query_embedding=query_embedding, limit=limit)
                
                # Group by topics
                topics = {}
                for record in result:
                    topic = record['topic']
                    if topic not in topics:
                        topics[topic] = []
                    topics[topic].append(f"- {record['role']}: {record['content']}")
                
                # Format context with better organization
                for topic, memories in topics.items():
                    context_parts.append(f"From {topic}:")
                    context_parts.extend(memories)
                
                return "\n".join(context_parts) if context_parts else ""
                
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return ""
    
    def get_topic_overview(self, user_id: str) -> Dict[str, Any]:
        """Get overview of user's topic structure"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)
                OPTIONAL MATCH (t)-[:CONTAINS_MEMORY]->(m:Memory)
                RETURN t.name as topic, t.created_at as created, count(m) as memory_count
                ORDER BY memory_count DESC, created DESC
                """, user_id=user_id)
                
                topics = []
                for record in result:
                    topics.append({
                        'name': record['topic'],
                        'memory_count': record['memory_count'],
                        'created': record['created']
                    })
                
                return {'topics': topics, 'total_topics': len(topics)}
                
        except Exception as e:
            print(f"Error getting topic overview: {e}")
            return {"topics": [], "topic_count": 0, "total_memories": 0}
    
    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for compatibility with app interface"""
        overview = self.get_topic_overview(user_id)
        return {
            "total_memories": overview["total_memories"],
            "top_topics": overview["topics"][:5],
            "avg_confidence": 0.85,  # Default confidence level
            "total_links": 0  # Cross-topic links count
        }

    def get_conversation_history(self, user_id: str, limit: int = 10) -> list:
        """Get recent conversation history for compatibility"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                RETURN m.role as role, m.content as content, m.created_at as timestamp
                ORDER BY m.created_at DESC
                LIMIT $limit
                """, user_id=user_id, limit=limit)
                
                return [{"role": record["role"], "content": record["content"], "timestamp": record["timestamp"]} 
                       for record in result]
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []

    def get_memory_count(self, user_id: str) -> int:
        """Get total memory count"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                RETURN count(m) as count
                """, user_id=user_id)
                
                record = result.single()
                return record["count"] if record else 0
        except Exception as e:
            print(f"Error getting memory count: {e}")
            return 0

    def get_relevant_memories(self, user_id: str, query: str, limit: int = 5) -> list:
        """Get relevant memories for a query"""
        context = self.retrieve_context(user_id, query, limit)
        if context:
            return [{"content": context, "relevance": 0.8}]
        return []

    def store_chat(self, user_id: str, messages: list):
        """Store chat messages in the neural memory system"""
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                self.store_conversation(user_id, msg["role"], msg["content"])


    def store_document(self, user_id: str, filename: str, content: str, file_type: str = "text") -> bool:
        """Store document as a separate entity from conversation memories"""
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (u:User {user_id: $user_id})
                    CREATE (d:Document {
                        filename: $filename,
                        content: $content,
                        file_type: $file_type,
                        uploaded_at: datetime(),
                        document_id: randomUUID()
                    })
                    CREATE (u)-[:UPLOADED]->(d)
                """, user_id=user_id, filename=filename, content=content, file_type=file_type)
                return True
        except Exception as e:
            print(f"Error storing document: {e}")
            return False

    def get_user_documents(self, user_id: str) -> list:
        """Get all documents uploaded by user"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:UPLOADED]->(d:Document)
                    RETURN d.document_id as id, d.filename as filename, 
                           d.file_type as type, d.uploaded_at as uploaded_at
                    ORDER BY d.uploaded_at DESC
                """, user_id=user_id)
                
                documents = []
                for record in result:
                    documents.append({
                        'id': record['id'],
                        'filename': record['filename'],
                        'type': record['type'],
                        'uploaded_at': record['uploaded_at']
                    })
                return documents
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []

    def delete_document(self, user_id: str, document_id: str) -> bool:
        """Delete a specific document"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:UPLOADED]->(d:Document {document_id: $document_id})
                    DETACH DELETE d
                    RETURN count(d) as deleted_count
                """, user_id=user_id, document_id=document_id)
                
                deleted_count = result.single()["deleted_count"]
                return deleted_count > 0
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    def search_documents(self, user_id: str, query: str, limit: int = 3) -> str:
        """Search user's documents for relevant content"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:UPLOADED]->(d:Document)
                    RETURN d.filename as filename, d.content as content, d.file_type as file_type
                """, user_id=user_id)
                
                documents = []
                for record in result:
                    documents.append({
                        'filename': record['filename'],
                        'content': record['content'],
                        'file_type': record['file_type']
                    })
                
                if not documents:
                    return ""
                
                # Search for relevant content using text similarity
                from utils import generate_embedding
                query_embedding = generate_embedding(query)
                
                relevant_docs = []
                for doc in documents:
                    if doc['content']:
                        # Split document into chunks for better matching
                        chunks = [doc['content'][i:i+500] for i in range(0, len(doc['content']), 400)]
                        
                        for chunk in chunks[:5]:  # Limit chunks per document
                            chunk_embedding = generate_embedding(chunk)
                            
                            # Calculate similarity
                            import numpy as np
                            similarity = np.dot(query_embedding, chunk_embedding) / (
                                np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                            )
                            
                            if similarity > 0.7:  # Threshold for relevance
                                relevant_docs.append({
                                    'filename': doc['filename'],
                                    'content': chunk,
                                    'similarity': similarity,
                                    'file_type': doc['file_type']
                                })
                
                # Sort by similarity and take top results
                relevant_docs.sort(key=lambda x: x['similarity'], reverse=True)
                relevant_docs = relevant_docs[:limit]
                
                if not relevant_docs:
                    return ""
                
                # Format results for AI context
                context = "\n\n=== RELEVANT DOCUMENTS ===\n"
                for doc in relevant_docs:
                    context += f"\nFrom {doc['filename']} ({doc['file_type']}):\n{doc['content']}\n"
                
                return context
                
        except Exception as e:
            print(f"Error searching documents: {e}")
            return ""

    def delete_memories_containing(self, user_id: str, search_term: str) -> int:
        """Delete memories containing specific text/keywords"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                    WHERE toLower(m.content) CONTAINS toLower($search_term)
                    WITH m, t
                    DETACH DELETE m
                    WITH t
                    MATCH (t) WHERE NOT (t)-[:CONTAINS_MEMORY]->()
                    DETACH DELETE t
                    RETURN count(*) as deleted_count
                """, user_id=user_id, search_term=search_term)
                
                deleted_count = result.single()["deleted_count"]
                return deleted_count
                
        except Exception as e:
            print(f"Error deleting memories: {e}")
            return 0

    def search_memories_by_keyword(self, user_id: str, keyword: str, limit: int = 10) -> list:
        """Search memories by keyword - faster than semantic search"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                    WHERE toLower(m.content) CONTAINS toLower($keyword)
                    RETURN m.content as content, m.role as role, m.created_at as timestamp, t.name as topic
                    ORDER BY m.created_at DESC
                    LIMIT $limit
                """, user_id=user_id, keyword=keyword, limit=limit)
                
                memories = []
                for record in result:
                    memories.append({
                        'content': record['content'],
                        'role': record['role'],
                        'timestamp': record['timestamp'],
                        'topic': record['topic']
                    })
                return memories
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []

    def delete_memories_by_date_range(self, user_id: str, start_date: str, end_date: str) -> int:
        """Delete memories within a date range (YYYY-MM-DD format)"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS]->(m:Memory)
                    WHERE date(m.timestamp) >= date($start_date) 
                    AND date(m.timestamp) <= date($end_date)
                    WITH m, t
                    DETACH DELETE m
                    WITH t
                    MATCH (t) WHERE NOT (t)-[:CONTAINS]->()
                    DETACH DELETE t
                    RETURN count(*) as deleted_count
                """, user_id=user_id, start_date=start_date, end_date=end_date)
                
                deleted_count = result.single()["deleted_count"]
                return deleted_count
                
        except Exception as e:
            print(f"Error deleting memories by date: {e}")
            return 0

    def set_user_name(self, user_id: str, name: str) -> bool:
        """Set or update user's name in a dedicated node"""
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (u:User {user_id: $user_id})
                    MERGE (u)-[:HAS_NAME]->(n:UserName)
                    SET n.name = $name, n.updated_at = datetime()
                """, user_id=user_id, name=name)
                return True
        except Exception as e:
            print(f"Error setting user name: {e}")
            return False

    def get_user_name(self, user_id: str) -> str:
        """Get user's stored name"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:HAS_NAME]->(n:UserName)
                    RETURN n.name as name
                """, user_id=user_id)
                
                record = result.single()
                return record['name'] if record else None
        except Exception as e:
            print(f"Error getting user name: {e}")
            return None

    def get_top_topics(self, user_id: str, limit: int = 5) -> list:
        """Get most discussed topics by memory count"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                    WITH t, count(m) as memory_count
                    RETURN t.name as topic, memory_count
                    ORDER BY memory_count DESC
                    LIMIT $limit
                """, user_id=user_id, limit=limit)
                
                topics = []
                for record in result:
                    topics.append({
                        'topic': record['topic'],
                        'memory_count': record['memory_count']
                    })
                return topics
        except Exception as e:
            print(f"Error getting top topics: {e}")
            return []

    def list_memories_about_topic(self, user_id: str, topic_keyword: str, limit: int = 10) -> list:
        """List memories about a specific topic or containing keywords"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {user_id: $user_id})-[:HAS_TOPIC]->(t:Topic)-[:CONTAINS_MEMORY]->(m:Memory)
                    WHERE toLower(t.name) CONTAINS toLower($topic_keyword) 
                    OR toLower(m.content) CONTAINS toLower($topic_keyword)
                    RETURN m.content as content, m.role as role, m.created_at as timestamp, t.name as topic
                    ORDER BY m.created_at DESC
                    LIMIT $limit
                """, user_id=user_id, topic_keyword=topic_keyword, limit=limit)
                
                memories = []
                for record in result:
                    memories.append({
                        'content': record['content'],
                        'role': record['role'],
                        'timestamp': record['timestamp'],
                        'topic': record['topic']
                    })
                return memories
        except Exception as e:
            print(f"Error listing memories: {e}")
            return []

    def parse_command(self, user_id: str, message: str) -> dict:
        """Parse user message for memory commands"""
        message_lower = message.lower().strip()
        
        # Slash commands
        if message_lower.startswith('/'):
            parts = message_lower[1:].split(' ', 1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            
            if command == "delete":
                return {"type": "delete", "target": args, "requires_confirmation": True}
            elif command == "search":
                return {"type": "search", "query": args}
            elif command == "list":
                if "topics" in args:
                    return {"type": "list_topics"}
                else:
                    return {"type": "list_memories", "query": args}
            
        # Natural language patterns
        elif any(phrase in message_lower for phrase in ["delete memories about", "delete all memories", "remove memories"]):
            # Extract topic/keyword after the delete phrase
            for phrase in ["delete memories about ", "delete all memories about ", "remove memories about "]:
                if phrase in message_lower:
                    target = message_lower.split(phrase, 1)[1].strip()
                    return {"type": "delete", "target": target, "requires_confirmation": True}
        
        elif any(phrase in message_lower for phrase in ["search for memories", "find memories", "search memories"]):
            # Extract search query
            for phrase in ["search for memories about ", "find memories about ", "search memories for "]:
                if phrase in message_lower:
                    query = message_lower.split(phrase, 1)[1].strip()
                    return {"type": "search", "query": query}
        
        elif any(phrase in message_lower for phrase in ["list top topics", "top discussed topics", "most discussed topics"]):
            return {"type": "list_topics"}
        
        elif message_lower.startswith("list ") and ("memories" in message_lower or "about" in message_lower):
            query = message_lower.replace("list memories about", "").replace("list", "").strip()
            return {"type": "list_memories", "query": query}
        
        return {"type": "none"}

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()