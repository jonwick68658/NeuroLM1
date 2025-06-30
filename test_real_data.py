"""
Test memory summarization with real user data
"""

import asyncio
from memory_summarizer import memory_summarizer

async def test_with_real_user():
    """Test summarization with actual user data from the system"""
    # Use Ryan's user ID from the database
    user_id = "24ca19e0-4695-4d68-a0c1-6daa98d8128e"
    
    print(f"Testing memory summarization for user ID: {user_id}")
    
    # Check for unprocessed memories
    memories = await memory_summarizer.get_unprocessed_memories(user_id, hours_back=48)
    print(f"Found {len(memories)} unprocessed memories")
    
    if memories:
        print("\nSample memories:")
        for i, memory in enumerate(memories[:3]):  # Show first 3
            print(f"{i+1}. [{memory['message_type']}] {memory['content'][:100]}...")
        
        # Run the summarization process
        print(f"\nProcessing daily summaries...")
        result = await memory_summarizer.process_user_daily_summaries(user_id)
        
        print(f"\nResults:")
        print(f"Status: {result['status']}")
        print(f"Summaries created: {result.get('summaries_created', 0)}")
        print(f"Memories processed: {result.get('memories_processed', 0)}")
        print(f"Total memories found: {result.get('total_memories_found', 0)}")
        
        return result
    else:
        print("No unprocessed memories found - system is working but no new data to summarize")
        return {"status": "no_new_memories", "processed": 0}

if __name__ == "__main__":
    asyncio.run(test_with_real_user())