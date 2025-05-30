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
        
        # Store chunk as DocumentChunk only
        session.run("""
        MATCH (d:Document {id: $doc_id})
        CREATE (c:DocumentChunk {
            id: $chunk_id,
            user_id: $user_id,
            content: $content,
            filename: $filename,
            chunk_index: $chunk_index,
            embedding: $embedding,
            created_at: datetime(),
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
        """Search through document content using semantic vector similarity"""
        try:
            from utils import generate_embedding
            query_embedding = generate_embedding(query)
            
            # If embedding generation fails, fall back to text search
            if not query_embedding or all(x == 0.0 for x in query_embedding):
                return self._text_search_documents(user_id, query, limit)
            
            return self._vector_search_documents(user_id, query_embedding, limit)
            
        except Exception as e:
            # Fallback to text search if vector search fails
            return self._text_search_documents(user_id, query, limit)
    
    def _text_search_documents(self, user_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Enhanced text-based search with multiple strategies"""
        with self.driver.session() as session:
            # Try exact phrase search first
            query_lower = query.lower()
            
            # Search for exact query matches
            result = session.run("""
            MATCH (c:DocumentChunk {user_id: $user_id})-[:BELONGS_TO]->(d:Document)
            WHERE toLower(c.content) CONTAINS $query_lower
            RETURN d.id AS doc_id, d.filename AS filename,
                   c.content AS chunk_content, c.chunk_index AS chunk_index, 1.0 as score,
                   d.created_at AS created_at
            ORDER BY created_at DESC
            LIMIT $limit
            """, user_id=user_id, query_lower=query_lower, limit=limit)
            
            matches = []
            for record in result:
                matches.append({
                    'doc_id': record['doc_id'],
                    'filename': record['filename'],
                    'chunk_content': record['chunk_content'],
                    'chunk_index': record['chunk_index'],
                    'similarity': record['score']
                })
            
            # If we don't have enough results, try keyword search
            if len(matches) < limit:
                keywords = [word.strip().lower() for word in query.split() if len(word.strip()) > 2]
                
                if keywords:
                    keyword_result = session.run("""
                    MATCH (c:DocumentChunk {user_id: $user_id})-[:BELONGS_TO]->(d:Document)
                    WHERE ANY(keyword IN $keywords WHERE toLower(c.content) CONTAINS keyword)
                    AND NOT (c.id IN $existing_ids)
                    RETURN d.id AS doc_id, d.filename AS filename,
                           c.content AS chunk_content, c.chunk_index AS chunk_index, 0.7 as score,
                           d.created_at AS created_at
                    ORDER BY created_at DESC
                    LIMIT $remaining_limit
                    """, 
                    user_id=user_id, 
                    keywords=keywords, 
                    existing_ids=[m['doc_id'] + '_' + str(m['chunk_index']) for m in matches],
                    remaining_limit=limit - len(matches))
                    
                    for record in keyword_result:
                        matches.append({
                            'doc_id': record['doc_id'],
                            'filename': record['filename'],
                            'chunk_content': record['chunk_content'],
                            'chunk_index': record['chunk_index'],
                            'similarity': record['score']
                        })
            
            return matches
    
    def _vector_search_documents(self, user_id: str, query_embedding: List[float], limit: int) -> List[Dict[str, Any]]:
        """Vector similarity search for document chunks"""
        with self.driver.session() as session:
            try:
                result = session.run("""
                CALL db.index.vector.queryNodes('document_embeddings', $limit, $query_embedding)
                YIELD node AS chunk, score AS similarity
                WHERE chunk.user_id = $user_id
                MATCH (chunk)-[:BELONGS_TO]->(d:Document)
                RETURN d.id AS doc_id, d.filename AS filename,
                       chunk.content AS chunk_content, chunk.chunk_index AS chunk_index,
                       similarity
                ORDER BY similarity DESC
                LIMIT $limit
                """, query_embedding=query_embedding, user_id=user_id, limit=limit)
                
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
                
            except Exception as e:
                # If vector search fails, fall back to text search
                return []
    
    def _get_recent_document_chunks(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent document chunks when no search results found"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (c:DocumentChunk {user_id: $user_id})-[:BELONGS_TO]->(d:Document)
            RETURN d.id AS doc_id, d.filename AS filename,
                   c.content AS chunk_content, c.chunk_index AS chunk_index
            ORDER BY d.created_at DESC, c.chunk_index ASC
            LIMIT $limit
            """, user_id=user_id, limit=limit)
            
            chunks = []
            for record in result:
                chunks.append({
                    'doc_id': record['doc_id'],
                    'filename': record['filename'],
                    'chunk_content': record['chunk_content'],
                    'chunk_index': record['chunk_index'],
                    'similarity': 0.5
                })
            
            return chunks
    
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