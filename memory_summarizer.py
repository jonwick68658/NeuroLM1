"""
Daily Memory Summarization Service
Processes daily conversations and creates intelligent summaries for enhanced memory retrieval
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from neo4j import GraphDatabase
from model_service import ModelService
import json

class MemorySummarizer:
    """Service for creating daily memory summaries"""
    
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
        self.max_memories_per_summary = 50
        self.summary_retention_days = 90
        self.min_memories_for_summary = 3  # Don't summarize trivial conversations
    
    def _setup_summary_indexes(self):
        """Create indexes for daily summary nodes"""
        try:
            with self.driver.session() as session:
                # Create vector index for summary embeddings
                session.run("""
                    CREATE VECTOR INDEX summary_embedding_index IF NOT EXISTS
                    FOR (s:DailySummary) ON (s.embedding)
                    OPTIONS {indexConfig: {
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }}
                """)
                
                # Create composite index for efficient querying
                session.run("""
                    CREATE INDEX summary_user_date_index IF NOT EXISTS
                    FOR (s:DailySummary) ON (s.user_id, s.date)
                """)
                
                print("✅ Summary indexes created successfully")
        except Exception as e:
            print(f"❌ Summary index setup failed: {e}")
            raise e
    
    async def get_unprocessed_memories(self, user_id: str, hours_back: int = 24) -> List[Dict]:
        """Get memories from the last N hours that haven't been summarized"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:IntelligentMemory)
                    WHERE m.user_id = $user_id 
                    AND m.timestamp >= $cutoff_time
                    AND NOT EXISTS((m)<-[:SUMMARIZES]-(:DailySummary))
                    RETURN m.id as id, m.content as content, m.conversation_id as conversation_id,
                           m.message_type as message_type, m.importance as importance,
                           m.timestamp as timestamp
                    ORDER BY m.timestamp ASC
                """, user_id=user_id, cutoff_time=cutoff_time)
                
                memories = []
                for record in result:
                    memories.append({
                        'id': record['id'],
                        'content': record['content'],
                        'conversation_id': record['conversation_id'],
                        'message_type': record['message_type'],
                        'importance': record['importance'],
                        'timestamp': record['timestamp']
                    })
                
                return memories
        except Exception as e:
            print(f"Error fetching unprocessed memories: {e}")
            return []
    
    def group_memories_by_topic(self, memories: List[Dict]) -> Dict[str, List[Dict]]:
        """Group memories by conversation/topic for targeted summarization"""
        grouped = {}
        
        for memory in memories:
            # Group by conversation_id first, then we'll determine topics
            conv_id = memory.get('conversation_id', 'general')
            if conv_id not in grouped:
                grouped[conv_id] = []
            grouped[conv_id].append(memory)
        
        return grouped
    
    async def generate_summary(self, memories: List[Dict], topic_context: str = "") -> Optional[str]:
        """Generate AI summary for a group of memories"""
        if len(memories) < self.min_memories_for_summary:
            return None
        
        # Prepare conversation context
        conversation_text = ""
        for memory in memories:
            timestamp = memory['timestamp'].strftime("%H:%M")
            msg_type = memory['message_type']
            content = memory['content']
            conversation_text += f"[{timestamp}] {msg_type}: {content}\n"
        
        # Create summarization prompt
        system_prompt = """You are an intelligent memory system creating concise daily summaries of conversations.

Your task:
1. Extract key facts, preferences, and important information
2. Identify main topics and themes discussed
3. Note any personal details, decisions, or future plans
4. Create a coherent summary that preserves context for future reference

Format your response as a clear, informative summary that would help recall this conversation later.
Keep it concise but comprehensive - focus on what would be useful to remember."""

        user_prompt = f"""Please summarize this conversation from today:

{topic_context}

Conversation:
{conversation_text}

Create a summary that captures the key points, facts, and context that would be valuable for future conversations."""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            summary = await self.model_service.chat_completion(
                messages=messages,
                model="openai/gpt-4o-mini"
            )
            
            return summary.strip()
        except Exception as e:
            print(f"Error generating summary: {e}")
            return None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings for summary text using OpenAI API"""
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
    
    async def store_daily_summary(self, user_id: str, summary_content: str, 
                                 memory_ids: List[str], topic: Optional[str] = None,
                                 sub_topic: Optional[str] = None) -> Optional[str]:
        """Store daily summary in Neo4j and link to original memories"""
        try:
            # Generate embedding for the summary
            embedding = self.generate_embedding(summary_content)
            if not embedding:
                print("Failed to generate embedding for summary")
                return None
            
            today = datetime.now().date()
            
            with self.driver.session() as session:
                # Create the daily summary node
                result = session.run("""
                    CREATE (s:DailySummary {
                        id: randomUUID(),
                        user_id: $user_id,
                        date: date($date),
                        topic: $topic,
                        sub_topic: $sub_topic,
                        summary_content: $summary_content,
                        memory_count: $memory_count,
                        embedding: $embedding,
                        created_at: datetime()
                    })
                    RETURN s.id as summary_id
                """, 
                user_id=user_id,
                date=today.isoformat(),
                topic=topic,
                sub_topic=sub_topic,
                summary_content=summary_content,
                memory_count=len(memory_ids),
                embedding=embedding
                )
                
                summary_record = result.single()
                if not summary_record:
                    return None
                
                summary_id = summary_record['summary_id']
                
                # Create relationships to original memories
                for memory_id in memory_ids:
                    session.run("""
                        MATCH (s:DailySummary {id: $summary_id})
                        MATCH (m:IntelligentMemory {id: $memory_id})
                        CREATE (s)-[:SUMMARIZES]->(m)
                    """, summary_id=summary_id, memory_id=memory_id)
                
                print(f"✅ Created daily summary {summary_id} for {len(memory_ids)} memories")
                return summary_id
                
        except Exception as e:
            print(f"Error storing daily summary: {e}")
            return None
    
    async def process_user_daily_summaries(self, user_id: str) -> Dict[str, any]:
        """Process daily summaries for a specific user"""
        print(f"Processing daily summaries for user: {user_id}")
        
        # Get unprocessed memories
        memories = await self.get_unprocessed_memories(user_id)
        
        if not memories:
            return {"status": "no_new_memories", "processed": 0}
        
        print(f"Found {len(memories)} unprocessed memories")
        
        # Group memories by conversation
        grouped_memories = self.group_memories_by_topic(memories)
        
        summaries_created = 0
        total_memories_processed = 0
        
        for conv_id, conv_memories in grouped_memories.items():
            if len(conv_memories) < self.min_memories_for_summary:
                print(f"Skipping conversation {conv_id} - only {len(conv_memories)} memories")
                continue
            
            # Generate summary for this conversation
            topic_context = f"Conversation ID: {conv_id}"
            summary = await self.generate_summary(conv_memories, topic_context)
            
            if summary:
                # Extract memory IDs
                memory_ids = [m['id'] for m in conv_memories]
                
                # Store the summary
                summary_id = await self.store_daily_summary(
                    user_id=user_id,
                    summary_content=summary,
                    memory_ids=memory_ids,
                    topic=None,  # We'll enhance topic detection later
                    sub_topic=None
                )
                
                if summary_id:
                    summaries_created += 1
                    total_memories_processed += len(conv_memories)
                    print(f"Created summary for conversation {conv_id}: {len(conv_memories)} memories")
        
        return {
            "status": "completed",
            "summaries_created": summaries_created,  
            "memories_processed": total_memories_processed,
            "total_memories_found": len(memories)
        }
    
    def close(self):
        """Close database connection"""
        self.driver.close()

# Initialize the summarizer (will be imported by main.py)
memory_summarizer = MemorySummarizer()