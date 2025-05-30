import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils import generate_embedding
import logging

class DocumentStorage:
    """Neo4j integration for document storage and retrieval"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    def store_document(self, user_id: str, filename: str, chunks: List[str]) -> tuple[str, List[str]]:
        """Store document with relationships to knowledge chunks"""
        if not chunks:
            raise ValueError("No chunks to store")
        
        with self.driver.session() as session:
            # Create document node
            doc_id = f"doc_{uuid.uuid4()}"
            session.run("""
            CREATE (d:Document {
                id: $doc_id,
                user_id: $user_id,
                filename: $filename,
                chunk_count: $chunk_count,
                created_at: datetime()
            })
            """, doc_id=doc_id, user_id=user_id, filename=filename, chunk_count=len(chunks))
            
            # Store chunks with embeddings
            chunk_ids = []
            for idx, content in enumerate(chunks):
                chunk_id = self._store_chunk(
                    session=session, 
                    content=content, 
                    user_id=user_id,
                    doc_id=doc_id,
                    chunk_index=idx,
                    filename=filename
                )
                chunk_ids.append(chunk_id)
            
            # Create document-level embedding from first few chunks
            combined_text = "\n\n".join(chunks[:3])  # Use first 3 chunks for doc embedding
            try:
                doc_embedding = generate_embedding(combined_text)
                session.run("""
                MATCH (d:Document {id: $doc_id})
                SET d.embedding = $embedding
                """, doc_id=doc_id, embedding=doc_embedding)
            except Exception as e:
                logging.warning(f"Failed to create document embedding: {str(e)}")
            
            return doc_id, chunk_ids
    
    def _store_chunk(self, session, content: str, user_id: str, doc_id: str, 
                     chunk_index: int, filename: str) -> str:
        """Store individual chunk with enhanced indexing"""
        chunk_id = f"chunk_{uuid.uuid4()}"
        
        try:
            embedding = generate_embedding(content)
        except Exception as e:
            logging.warning(f"Failed to generate embedding for chunk {chunk_index}: {str(e)}")
            embedding = None
        
        # Store chunk as both Memory and DocumentChunk for compatibility
        session.run("""
        MATCH (d:Document {id: $doc_id})
        CREATE (c:Memory:DocumentChunk {
            id: $chunk_id,
            user_id: $user_id,
            content: $content,
            source: $filename,
            role: 'document',
            created_at: datetime(),
            chunk_index: $chunk_index,
            embedding: $embedding,
            access_count: 0,
            confidence: 1.0,
            last_accessed: datetime()
        })
        CREATE (c)-[:BELONGS_TO]->(d)
        """, 
        chunk_id=chunk_id, 
        user_id=user_id, 
        content=content, 
        chunk_index=chunk_index,
        doc_id=doc_id, 
        embedding=embedding,
        filename=filename)
        
        return chunk_id
    
    def get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all documents for a user"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (d:Document {user_id: $user_id})
            RETURN d.id AS id, d.filename AS filename, 
                   d.created_at AS created_at, d.chunk_count AS chunk_count
            ORDER BY d.created_at DESC
            """, user_id=user_id)
            
            documents = []
            for record in result:
                documents.append({
                    'id': record['id'],
                    'filename': record['filename'],
                    'created_at': record['created_at'],
                    'chunk_count': record['chunk_count']
                })
            
            return documents
    
    def get_document_chunks(self, doc_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get document chunks with content"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (d:Document {id: $doc_id, user_id: $user_id})<-[:BELONGS_TO]-(c:DocumentChunk)
            RETURN c.id AS id, c.content AS content, c.chunk_index AS chunk_index,
                   c.source AS source
            ORDER BY c.chunk_index
            """, doc_id=doc_id, user_id=user_id)
            
            chunks = []
            for record in result:
                chunks.append({
                    'id': record['id'],
                    'content': record['content'],
                    'chunk_index': record['chunk_index'],
                    'source': record['source']
                })
            
            return chunks
    
    def delete_document(self, doc_id: str, user_id: str) -> bool:
        """Delete document and all associated chunks"""
        with self.driver.session() as session:
            # Delete chunks first
            session.run("""
            MATCH (d:Document {id: $doc_id, user_id: $user_id})<-[:BELONGS_TO]-(c:DocumentChunk)
            DETACH DELETE c
            """, doc_id=doc_id, user_id=user_id)
            
            # Delete document
            result = session.run("""
            MATCH (d:Document {id: $doc_id, user_id: $user_id})
            DETACH DELETE d
            RETURN count(d) AS deleted_count
            """, doc_id=doc_id, user_id=user_id)
            
            return result.single()['deleted_count'] > 0
    
    def search_documents(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search through document content"""
        try:
            query_embedding = generate_embedding(query)
        except Exception as e:
            logging.warning(f"Failed to generate query embedding: {str(e)}")
            # Fallback to text search
            return self._text_search_documents(user_id, query, limit)
        
        with self.driver.session() as session:
            # Vector similarity search through chunks
            result = session.run("""
            MATCH (c:DocumentChunk {user_id: $user_id})-[:BELONGS_TO]->(d:Document)
            WHERE c.embedding IS NOT NULL
            WITH c, d, gds.similarity.cosine(c.embedding, $query_embedding) AS similarity
            WHERE similarity > 0.7
            RETURN DISTINCT d.id AS doc_id, d.filename AS filename, 
                   c.content AS chunk_content, c.chunk_index AS chunk_index,
                   similarity
            ORDER BY similarity DESC
            LIMIT $limit
            """, user_id=user_id, query_embedding=query_embedding, limit=limit)
            
            matches = []
            for record in result:
                matches.append({
                    'doc_id': record['doc_id'],
                    'filename': record['filename'],
                    'chunk_content': record['chunk_content'],
                    'chunk_index': record['chunk_index'],
                    'similarity': record['similarity']
                })
            
            return matches
    
    def _text_search_documents(self, user_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback text-based search"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (c:DocumentChunk {user_id: $user_id})-[:BELONGS_TO]->(d:Document)
            WHERE toLower(c.content) CONTAINS toLower($query)
            RETURN DISTINCT d.id AS doc_id, d.filename AS filename,
                   c.content AS chunk_content, c.chunk_index AS chunk_index
            ORDER BY d.created_at DESC
            LIMIT $limit
            """, user_id=user_id, query=query, limit=limit)
            
            matches = []
            for record in result:
                matches.append({
                    'doc_id': record['doc_id'],
                    'filename': record['filename'],
                    'chunk_content': record['chunk_content'],
                    'chunk_index': record['chunk_index'],
                    'similarity': 0.8  # Default similarity for text matches
                })
            
            return matches
    
    def get_document_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's document collection"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (d:Document {user_id: $user_id})
            OPTIONAL MATCH (d)<-[:BELONGS_TO]-(c:DocumentChunk)
            RETURN count(DISTINCT d) AS total_documents,
                   count(c) AS total_chunks,
                   sum(d.chunk_count) AS total_chunk_count
            """, user_id=user_id)
            
            record = result.single()
            return {
                'total_documents': record['total_documents'] or 0,
                'total_chunks': record['total_chunks'] or 0,
                'total_chunk_count': record['total_chunk_count'] or 0
            }