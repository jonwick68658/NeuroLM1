"""
Direct test of memory summarization with existing data
"""

import asyncio
import os
from datetime import datetime, timedelta
from neo4j import GraphDatabase
from memory_summarizer import memory_summarizer

async def test_summarization_with_existing_data():
    """Test summarization by processing some existing memories"""
    user_id = "24ca19e0-4695-4d68-a0c1-6daa98d8128e"
    
    print("Testing summarization with existing memories...")
    
    # Get some recent memories, ignoring the "already processed" filter for testing
    try:
        with memory_summarizer.driver.session() as session:
            result = session.run("""
                MATCH (m:IntelligentMemory)
                WHERE m.user_id = $user_id 
                RETURN m.id as id, m.content as content, m.conversation_id as conversation_id,
                       m.message_type as message_type, m.importance as importance,
                       m.timestamp as timestamp
                ORDER BY m.timestamp DESC 
                LIMIT 10
            """, user_id=user_id)
            
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
            
            print(f"Found {len(memories)} memories to test with")
            
            if memories:
                print("\nSample memory contents:")
                for i, memory in enumerate(memories[:3]):
                    content = memory['content'][:80] + "..." if len(memory['content']) > 80 else memory['content']
                    print(f"  {i+1}. [{memory['message_type']}] {content}")
                
                # Group memories by conversation
                grouped = memory_summarizer.group_memories_by_topic(memories)
                print(f"\nGrouped into {len(grouped)} conversations")
                
                # Test summarization on the first group with enough memories
                for conv_id, conv_memories in grouped.items():
                    if len(conv_memories) >= 3:  # Use the min threshold
                        print(f"\nTesting summarization for conversation: {conv_id}")
                        print(f"Processing {len(conv_memories)} memories...")
                        
                        # Generate summary
                        summary = await memory_summarizer.generate_summary(conv_memories, f"Conversation: {conv_id}")
                        
                        if summary:
                            print(f"\nGenerated summary:")
                            print(f"{summary[:200]}...")
                            
                            # Test storing the summary
                            memory_ids = [m['id'] for m in conv_memories]
                            summary_id = await memory_summarizer.store_daily_summary(
                                user_id=user_id,
                                summary_content=summary,
                                memory_ids=memory_ids,
                                topic="test_topic",
                                sub_topic=None
                            )
                            
                            if summary_id:
                                print(f"Successfully stored summary with ID: {summary_id}")
                                return {"status": "success", "summary_id": summary_id}
                            else:
                                print("Failed to store summary")
                                return {"status": "storage_failed"}
                        else:
                            print("Failed to generate summary")
                        
                        break  # Test with just one conversation group
                else:
                    print("No conversation groups had enough memories for summarization")
                    return {"status": "insufficient_memories"}
            else:
                print("No memories found for user")
                return {"status": "no_memories"}
                
    except Exception as e:
        print(f"Error during testing: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_summarization_with_existing_data())
    print(f"\nFinal result: {result}")