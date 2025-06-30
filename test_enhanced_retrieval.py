"""
Test enhanced memory retrieval with daily summaries
"""

import asyncio
from intelligent_memory import IntelligentMemorySystem

async def test_enhanced_retrieval():
    """Test that memory retrieval includes both raw memories and daily summaries"""
    
    # Initialize memory system
    memory_system = IntelligentMemorySystem()
    user_id = "24ca19e0-4695-4d68-a0c1-6daa98d8128e"
    
    print("Testing enhanced memory retrieval...")
    
    # Test queries that should retrieve both memories and summaries
    test_queries = [
        "What do you know about Ryan?",
        "Tell me about our previous conversations",
        "What have we discussed recently?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            context = await memory_system.retrieve_memory(
                query=query,
                user_id=user_id,
                conversation_id=None,
                limit=5
            )
            
            if context:
                print(f"Retrieved context ({len(context)} chars):")
                print(f"{context[:300]}...")
                
                # Check if both types are present
                has_memories = "Previous message:" in context
                has_summaries = "Daily summary:" in context
                
                print(f"Contains raw memories: {has_memories}")
                print(f"Contains daily summaries: {has_summaries}")
            else:
                print("No context retrieved")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Clean up
    memory_system.close()
    
    print("\nEnhanced retrieval test completed")

if __name__ == "__main__":
    asyncio.run(test_enhanced_retrieval())