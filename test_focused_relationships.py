"""
Focused test for relationship analyzer core functionality
"""

import asyncio
from relationship_analyzer import relationship_analyzer

async def test_with_small_dataset():
    """Test relationship analysis with a very small dataset"""
    user_id = "24ca19e0-4695-4d68-a0c1-6daa98d8128e"
    
    print("Testing with small dataset (5 memories)...")
    
    try:
        result = await relationship_analyzer.analyze_memory_relationships(user_id, limit=5)
        print(f"Result: {result}")
        return result['status'] != 'error'
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_with_small_dataset())
    print(f"Test {'passed' if success else 'failed'}")