"""
Test script for Memory Summarizer Service
"""

import asyncio
from memory_summarizer import memory_summarizer

async def test_summarizer_initialization():
    """Test basic initialization and index setup"""
    print("Testing Memory Summarizer initialization...")
    
    try:
        # Test index setup
        memory_summarizer._setup_summary_indexes()
        print("✅ Index setup successful")
        
        # Test database connection
        with memory_summarizer.driver.session() as session:
            result = session.run("RETURN 'connection test' as test")
            record = result.single()
            if record and record['test'] == 'connection test':
                print("✅ Database connection successful")
            else:
                print("❌ Database connection failed")
                return False
                
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        return False
    
    return True

async def test_memory_fetching():
    """Test fetching unprocessed memories"""
    print("\nTesting memory fetching...")
    
    try:
        # Use a test user ID - we'll need a real one from the system
        test_user_id = "test-user-123"  # This won't exist yet, but tests the query
        
        memories = await memory_summarizer.get_unprocessed_memories(test_user_id)
        print(f"✅ Memory fetching successful - found {len(memories)} memories for test user")
        
        return True
    except Exception as e:
        print(f"❌ Memory fetching test failed: {e}")
        return False

async def run_tests():
    """Run all tests"""
    print("=== Memory Summarizer Tests ===\n")
    
    tests = [
        test_summarizer_initialization,
        test_memory_fetching
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    all_passed = True
    for result in results:
        if not result:
            all_passed = False
            break
    
    if all_passed:
        print("✅ All tests passed - ready to proceed")
    else:
        print("❌ Some tests failed - need to investigate")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_tests())