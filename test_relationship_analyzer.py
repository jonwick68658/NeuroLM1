"""
Test script for Relationship Analyzer
"""

import asyncio
from relationship_analyzer import relationship_analyzer

async def test_analyzer_initialization():
    """Test basic initialization and index setup"""
    print("Testing Relationship Analyzer initialization...")
    
    try:
        # Test index setup
        relationship_analyzer._setup_relationship_indexes()
        print("✅ Relationship indexes created successfully")
        
        # Test database connection
        with relationship_analyzer.driver.session() as session:
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

async def test_topic_extraction():
    """Test AI topic extraction functionality"""
    print("\nTesting topic extraction...")
    
    test_content = "I love cooking Italian pasta dishes with fresh tomatoes and basil"
    
    try:
        topics = await relationship_analyzer.extract_topics_from_content(test_content)
        print(f"✅ Topic extraction successful - found topics: {topics}")
        
        if topics and len(topics) > 0:
            return True
        else:
            print("❌ No topics extracted")
            return False
            
    except Exception as e:
        print(f"❌ Topic extraction test failed: {e}")
        return False

async def test_memory_relationship_analysis():
    """Test memory relationship analysis with real data"""
    print("\nTesting memory relationship analysis...")
    
    user_id = "24ca19e0-4695-4d68-a0c1-6daa98d8128e"
    
    try:
        result = await relationship_analyzer.analyze_memory_relationships(user_id, limit=20)
        print(f"✅ Memory relationship analysis completed")
        print(f"Status: {result['status']}")
        print(f"Memories analyzed: {result.get('memories_analyzed', 0)}")
        print(f"Topic clusters created: {result.get('topic_clusters_created', 0)}")
        
        return result['status'] in ['completed', 'insufficient_data']
        
    except Exception as e:
        print(f"❌ Memory relationship analysis failed: {e}")
        return False

async def run_relationship_tests():
    """Run all relationship analyzer tests"""
    print("=== Relationship Analyzer Tests ===\n")
    
    tests = [
        test_analyzer_initialization,
        test_topic_extraction,
        test_memory_relationship_analysis
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
        print("✅ All relationship analyzer tests passed")
    else:
        print("❌ Some tests failed")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_relationship_tests())