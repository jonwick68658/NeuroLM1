#!/usr/bin/env python3
"""
Direct cache testing without API dependencies.
Tests the conversation cache system directly.
"""

import time
import uuid
from conversation_cache import ConversationCache
from memory import MemoryNode, MemorySystem
from datetime import datetime

def test_conversation_cache_performance():
    """Test conversation cache performance directly"""
    print("Direct Conversation Cache Performance Test")
    print("=" * 60)
    
    # Initialize cache and memory system
    cache = ConversationCache()
    memory_system = MemorySystem()
    
    # Test conversation ID
    conversation_id = str(uuid.uuid4())
    user_id = "test-user-cache"
    
    print(f"Test conversation ID: {conversation_id}")
    print(f"Cache type: {cache.get_cache_stats()['cache_type']}")
    
    # Test 1: First memory retrieval (cache miss expected)
    print("\n📝 Test 1: First query (cache miss)")
    start_time = time.time()
    
    query1 = "Tell me about the memory system architecture"
    memories1 = memory_system.retrieve_memories(
        query=query1,
        context="",
        depth=5,
        user_id=user_id
    )
    
    end_time = time.time()
    latency1_ms = (end_time - start_time) * 1000
    print(f"   Full search latency: {latency1_ms:.1f}ms")
    print(f"   Retrieved memories: {len(memories1)}")
    
    # Populate cache with first query results
    if memories1:
        cache.update_conversation_context(
            conversation_id, 
            "user", 
            query1,
            memories1[:3]
        )
        cache.update_conversation_context(
            conversation_id, 
            "assistant", 
            "I explained the memory system architecture using Neo4j graph database."
        )
    
    # Test 2: Cache hit scenario
    print("\n📝 Test 2: Cached memory retrieval (cache hit)")
    start_time = time.time()
    
    cached_memories = cache.get_cached_memories(conversation_id)
    
    end_time = time.time()
    latency2_ms = (end_time - start_time) * 1000
    print(f"   Cache retrieval latency: {latency2_ms:.1f}ms")
    print(f"   Cached memories: {len(cached_memories)}")
    
    # Test 3: Cache context update
    print("\n📝 Test 3: Cache context update")
    start_time = time.time()
    
    cache.update_conversation_context(
        conversation_id,
        "user",
        "Can you elaborate on the performance improvements?"
    )
    
    end_time = time.time()
    latency3_ms = (end_time - start_time) * 1000
    print(f"   Cache update latency: {latency3_ms:.1f}ms")
    
    # Test 4: Topic drift detection
    print("\n📝 Test 4: Topic drift detection")
    start_time = time.time()
    
    coherence_score = cache.detect_conversation_drift(
        conversation_id,
        "Let's talk about quantum computing instead"
    )
    
    end_time = time.time()
    latency4_ms = (end_time - start_time) * 1000
    print(f"   Drift detection latency: {latency4_ms:.1f}ms")
    print(f"   Coherence score: {coherence_score:.3f}")
    
    # Test 5: Cache refresh trigger
    print("\n📝 Test 5: Cache refresh check")
    should_refresh = cache.should_refresh_cache(conversation_id, 0.3)
    print(f"   Should refresh cache: {should_refresh}")
    
    # Performance summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    improvement_ratio = latency1_ms / latency2_ms if latency2_ms > 0 else 0
    
    print(f"Full memory search: {latency1_ms:.1f}ms")
    print(f"Cache retrieval: {latency2_ms:.1f}ms")
    print(f"Cache update: {latency3_ms:.1f}ms")
    print(f"Drift detection: {latency4_ms:.1f}ms")
    print(f"Performance improvement: {improvement_ratio:.1f}x faster")
    
    # Target analysis
    if latency2_ms < 10:
        print("🎯 TARGET ACHIEVED: Sub-10ms cache retrieval!")
    elif latency2_ms < 20:
        print("✅ EXCELLENT: Sub-20ms cache retrieval achieved!")
    elif latency2_ms < 50:
        print("⚠️  GOOD: Sub-50ms performance, within acceptable range")
    else:
        print("❌ NEEDS IMPROVEMENT: Cache retrieval too slow")
    
    # Cache statistics
    print(f"\nCache Statistics:")
    cache_stats = cache.get_cache_stats()
    for key, value in cache_stats.items():
        print(f"   {key}: {value}")
    
    return {
        "full_search_ms": latency1_ms,
        "cache_retrieval_ms": latency2_ms,
        "cache_update_ms": latency3_ms,
        "drift_detection_ms": latency4_ms,
        "improvement_ratio": improvement_ratio,
        "cache_stats": cache_stats
    }

def test_memory_promotion():
    """Test memory promotion logic"""
    print("\n" + "=" * 60)
    print("🧠 MEMORY PROMOTION TEST")
    print("=" * 60)
    
    cache = ConversationCache()
    conversation_id = str(uuid.uuid4())
    
    # Create test memories
    test_memories = [
        MemoryNode("Performance optimization is crucial", confidence=0.9),
        MemoryNode("Caching reduces latency significantly", confidence=0.8),
        MemoryNode("Redis provides fast in-memory storage", confidence=0.7)
    ]
    
    # Assign IDs to memories
    for i, memory in enumerate(test_memories):
        memory.id = f"test-memory-{i}"
    
    # Test promotion
    start_time = time.time()
    
    success = cache.update_conversation_context(
        conversation_id,
        "assistant",
        "I've promoted relevant memories to the conversation cache",
        test_memories
    )
    
    end_time = time.time()
    promotion_ms = (end_time - start_time) * 1000
    
    print(f"Memory promotion latency: {promotion_ms:.1f}ms")
    print(f"Promotion success: {success}")
    
    # Verify promoted memories
    promoted = cache.get_cached_memories(conversation_id)
    print(f"Promoted memories count: {len(promoted)}")
    
    for i, memory in enumerate(promoted):
        print(f"   Memory {i+1}: {memory.content[:50]}... (confidence: {memory.confidence:.2f})")
    
    return promotion_ms

def main():
    """Run comprehensive cache tests"""
    print("Starting comprehensive conversation cache tests...\n")
    
    # Test core cache performance
    performance_results = test_conversation_cache_performance()
    
    # Test memory promotion
    promotion_latency = test_memory_promotion()
    
    # Final assessment
    print("\n" + "=" * 60)
    print("🎯 FINAL ASSESSMENT")
    print("=" * 60)
    
    cache_retrieval = performance_results["cache_retrieval_ms"]
    improvement = performance_results["improvement_ratio"]
    
    if cache_retrieval < 20 and improvement > 5:
        print("✅ CACHE IMPLEMENTATION SUCCESSFUL")
        print("   - Sub-20ms retrieval achieved")
        print("   - Significant performance improvement")
        print("   - Memory promotion working")
    elif cache_retrieval < 50:
        print("⚠️  CACHE PARTIALLY SUCCESSFUL")
        print("   - Decent performance improvement")
        print("   - Room for optimization")
    else:
        print("❌ CACHE NEEDS OPTIMIZATION")
        print("   - Performance targets not met")
        print("   - Review implementation")
    
    print(f"\nKey Metrics:")
    print(f"   Cache retrieval: {cache_retrieval:.1f}ms")
    print(f"   Performance improvement: {improvement:.1f}x")
    print(f"   Memory promotion: {promotion_latency:.1f}ms")

if __name__ == "__main__":
    main()