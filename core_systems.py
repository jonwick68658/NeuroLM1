#!/usr/bin/env python3
"""
Core Systems Rebuild for NeuroLM
Rebuilding memory storage, document processing, and context retrieval
"""

import os
from neo4j import GraphDatabase
from datetime import datetime
from utils import generate_embedding
import uuid

class CoreMemorySystem:
    """Rebuilt memory system with proper storage and retrieval"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def store_conversation_message(self, user_id: str, role: str, content: str) -> str:
        """Store conversation message with full content preservation"""
        print(f"🧠 Storing {role} message for {user_id}: {content[:50]}...")
        
        try:
            # Generate embedding
            embedding = generate_embedding(content)
            message_id = str(uuid.uuid4())
            
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (m:Memory {
                    id: $message_id,
                    user_id: $user_id,
                    role: $role,
                    content: $content,
                    embedding: $embedding,
                    timestamp: datetime(),
                    access_count: 0,
                    strength: 1.0
                })
                CREATE (u)-[:CREATED]->(m)
                RETURN m.id as memory_id
                """, 
                user_id=user_id, 
                message_id=message_id,
                role=role, 
                content=content, 
                embedding=embedding
                )
                
                record = result.single()
                if record:
                    print(f"   ✓ Stored memory: {record['memory_id']}")
                    return record['memory_id']
                else:
                    print(f"   ❌ Failed to store memory")
                    return None
                    
        except Exception as e:
            print(f"   ❌ Error storing memory: {e}")
            return None
    
    def retrieve_relevant_memories(self, user_id: str, query: str, limit: int = 5) -> list:
        """Enhanced memory retrieval with full content"""
        print(f"🔍 Retrieving memories for query: {query[:30]}...")
        
        try:
            query_embedding = generate_embedding(query)
            
            with self.driver.session() as session:
                # Use vector similarity search
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                WHERE m.embedding IS NOT NULL
                WITH m, vector.similarity.cosine(m.embedding, $query_embedding) AS score
                WHERE score > 0.7
                SET m.access_count = m.access_count + 1
                RETURN m.role as role, m.content as content, m.timestamp as timestamp, score
                ORDER BY score DESC
                LIMIT $limit
                """, 
                user_id=user_id, 
                query_embedding=query_embedding, 
                limit=limit
                )
                
                memories = []
                for record in result:
                    memories.append({
                        'role': record['role'],
                        'content': record['content'],
                        'timestamp': record['timestamp'],
                        'score': record['score']
                    })
                
                print(f"   ✓ Found {len(memories)} relevant memories")
                return memories
                
        except Exception as e:
            print(f"   ❌ Error retrieving memories: {e}")
            return []
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> list:
        """Get recent conversation history with full content"""
        print(f"📚 Getting conversation history for {user_id}...")
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                RETURN m.role as role, m.content as content, m.timestamp as timestamp
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """, user_id=user_id, limit=limit)
                
                history = []
                for record in result:
                    history.append({
                        'role': record['role'],
                        'content': record['content'],
                        'timestamp': record['timestamp']
                    })
                
                print(f"   ✓ Retrieved {len(history)} conversation messages")
                return history
                
        except Exception as e:
            print(f"   ❌ Error getting history: {e}")
            return []

class CoreDocumentSystem:
    """Rebuilt document system with proper chunk linking"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def store_document(self, user_id: str, filename: str, content_chunks: list) -> str:
        """Store document with proper chunk relationships"""
        print(f"📄 Storing document {filename} with {len(content_chunks)} chunks...")
        
        try:
            doc_id = str(uuid.uuid4())
            
            with self.driver.session() as session:
                # Create document node
                session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (d:Document {
                    id: $doc_id,
                    user_id: $user_id,
                    filename: $filename,
                    upload_timestamp: datetime(),
                    chunk_count: $chunk_count
                })
                CREATE (u)-[:UPLOADED]->(d)
                """, 
                user_id=user_id, 
                doc_id=doc_id, 
                filename=filename, 
                chunk_count=len(content_chunks)
                )
                
                # Store chunks with relationships
                for i, chunk_content in enumerate(content_chunks):
                    chunk_id = str(uuid.uuid4())
                    embedding = generate_embedding(chunk_content)
                    
                    session.run("""
                    MATCH (d:Document {id: $doc_id})
                    CREATE (c:DocumentChunk {
                        id: $chunk_id,
                        user_id: $user_id,
                        doc_id: $doc_id,
                        filename: $filename,
                        chunk_index: $chunk_index,
                        content: $chunk_content,
                        embedding: $embedding,
                        created_at: datetime()
                    })
                    CREATE (d)-[:CONTAINS_CHUNK]->(c)
                    """, 
                    doc_id=doc_id,
                    chunk_id=chunk_id,
                    user_id=user_id,
                    filename=filename,
                    chunk_index=i,
                    chunk_content=chunk_content,
                    embedding=embedding
                    )
                
                print(f"   ✓ Stored document {doc_id} with {len(content_chunks)} chunks")
                return doc_id
                
        except Exception as e:
            print(f"   ❌ Error storing document: {e}")
            return None
    
    def search_documents(self, user_id: str, query: str, limit: int = 3) -> list:
        """Search document chunks with proper scoring"""
        print(f"📄 Searching documents for: {query[:30]}...")
        
        try:
            query_embedding = generate_embedding(query)
            
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)-[:CONTAINS_CHUNK]->(c:DocumentChunk)
                WHERE c.embedding IS NOT NULL
                WITH c, vector.similarity.cosine(c.embedding, $query_embedding) AS score
                WHERE score > 0.6
                RETURN c.filename as filename, c.content as content, score
                ORDER BY score DESC
                LIMIT $limit
                """, 
                user_id=user_id, 
                query_embedding=query_embedding, 
                limit=limit
                )
                
                documents = []
                for record in result:
                    documents.append({
                        'filename': record['filename'],
                        'content': record['content'],
                        'score': record['score']
                    })
                
                print(f"   ✓ Found {len(documents)} relevant document chunks")
                return documents
                
        except Exception as e:
            print(f"   ❌ Error searching documents: {e}")
            return []
    
    def get_user_documents(self, user_id: str) -> list:
        """Get list of user's documents"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:UPLOADED]->(d:Document)
                RETURN d.filename as filename, d.id as doc_id, d.chunk_count as chunks
                ORDER BY d.upload_timestamp DESC
                """, user_id=user_id)
                
                docs = []
                for record in result:
                    docs.append({
                        'filename': record['filename'],
                        'doc_id': record['doc_id'],
                        'chunks': record['chunks']
                    })
                
                return docs
                
        except Exception as e:
            print(f"Error getting user documents: {e}")
            return []

def test_core_systems():
    """Test the rebuilt core systems"""
    print("🧪 TESTING CORE SYSTEMS")
    print("=" * 50)
    
    memory_system = CoreMemorySystem()
    doc_system = CoreDocumentSystem()
    
    user_id = "user_Ryan"
    
    # Test memory storage
    print("\n1. Testing Memory Storage...")
    memory_id1 = memory_system.store_conversation_message(user_id, "user", "My name is Ryan")
    memory_id2 = memory_system.store_conversation_message(user_id, "assistant", "Hello Ryan! Nice to meet you.")
    memory_id3 = memory_system.store_conversation_message(user_id, "user", "I mentioned the operator elite program earlier")
    
    # Test memory retrieval
    print("\n2. Testing Memory Retrieval...")
    name_memories = memory_system.retrieve_relevant_memories(user_id, "What's my name?", 3)
    print(f"Name query results: {len(name_memories)}")
    for mem in name_memories:
        print(f"  {mem['role']}: {mem['content'][:50]}... (score: {mem['score']:.3f})")
    
    # Test conversation history
    print("\n3. Testing Conversation History...")
    history = memory_system.get_conversation_history(user_id, 5)
    print(f"History results: {len(history)}")
    for msg in history:
        print(f"  {msg['role']}: {msg['content'][:50]}...")
    
    # Test document storage
    print("\n4. Testing Document Storage...")
    test_chunks = [
        "This is the first chunk of a test document about business strategies.",
        "The second chunk discusses operator elite programs and advanced training.",
        "The final chunk covers implementation and best practices."
    ]
    doc_id = doc_system.store_document(user_id, "test_document.pdf", test_chunks)
    
    # Test document search
    print("\n5. Testing Document Search...")
    doc_results = doc_system.search_documents(user_id, "operator elite", 3)
    print(f"Document search results: {len(doc_results)}")
    for doc in doc_results:
        print(f"  {doc['filename']}: {doc['content'][:50]}... (score: {doc['score']:.3f})")
    
    print("\n✅ CORE SYSTEMS TESTING COMPLETE")
    
    memory_system.driver.close()
    doc_system.driver.close()

if __name__ == "__main__":
    test_core_systems()