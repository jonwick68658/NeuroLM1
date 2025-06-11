#!/usr/bin/env python3
"""
Test integrated conversation caching within the main chat flow.
Simulates the actual chat endpoint behavior with caching.
"""

import time
import uuid
from conversation_cache import ConversationCache
from memory import MemorySystem, MemoryNode
from model_service import ModelService

def simulate_chat_with_cache(message: str, conversation_id: str, user_id: str):
    """Simulate the chat_with_memory function with caching enabled"""
    print(f"\n💬 Processing: '{message[:50]}...'")
    
    # Initialize systems
    conv_cache = ConversationCache()
    memory_system = MemorySystem()
    model_service = ModelService()
    
    # Tiered memory retrieval with conversation caching
    relevant_memories = []
    cache_start_time = time.time()
    
    # Level 1: Check conversation cache first
    cached_memories = conv_cache.get_cached_memories(conversation_id)
    if cached_memories and len(cached_memories) >= 3:
        relevant_memories = cached_memories[:5]
        print(f"   🎯 Cache hit - retrieved {len(relevant_memories)} memories")
    else:
        # Level 2: Full memory search with cache population
        print(f"   🔍 Cache miss - performing full search")
        relevant_memories = memory_system.retrieve_memories(
            query=message,
            context="",
            depth=5,
            user_id=user_id
        )
        
        # Promote top memories to conversation cache
        if relevant_memories:
            conv_cache.update_conversation_context(
                conversation_id, 
                "system", 
                f"Context query: {message}",
                relevant_memories[:3]
            )
    
    cache_end_time = time.time()
    cache_time_ms = (cache_end_time - cache_start_time) * 1000
    
    # Build context from memories
    context = ""
    if relevant_memories:
        context = "\n".join([f"- {mem.content}" for mem in relevant_memories[:5]])
    
    # Generate response (simplified)
    response_text = f"I understand your question about '{message[:30]}...' "
    if relevant_memories:
        response_text += f"Based on {len(relevant_memories)} relevant memories, "
    response_text += "I can help you with that topic."
    
    # Update conversation cache with new messages
    conv_cache.update_conversation_context(conversation_id, 'user', message)
    conv_cache.update_conversation_context(conversation_id, 'assistant', response_text)
    
    return {
        "response": response_text,
        "memory_retrieval_ms": cache_time_ms,
        "memories_used": len(relevant_memories),
        "cache_hit": len(cached_memories) >= 3 if cached_memories else False,
        "conversation_id": conversation_id
    }

def test_conversation_flow():
    """Test a complete conversation flow with caching"""
    print("Testing Integrated Conversation Cache Flow")
    print("=" * 60)
    
    # Setup
    conversation_id = str(uuid.uuid4())
    user_id = "test-user-integrated"
    
    # Conversation sequence
    messages = [
        "Hello, I want to learn about AI memory systems",
        "How do memory systems improve performance?",
        "What about conversation caching specifically?",
        "Can you explain the technical implementation?",
        "Let's switch topics - tell me about quantum computing"
    ]
    
    results = []
    
    for i, message in enumerate(messages, 1):
        print(f"\n--- Message {i} ---")
        result = simulate_chat_with_cache(message, conversation_id, user_id)
        results.append(result)
        
        print(f"   Memory retrieval: {result['memory_retrieval_ms']:.1f}ms")
        print(f"   Cache hit: {result['cache_hit']}")
        print(f"   Memories used: {result['memories_used']}")
        
        # Small delay to simulate real conversation
        time.sleep(0.1)
    
    # Analysis
    print("\n" + "=" * 60)
    print("📊 CONVERSATION FLOW ANALYSIS")
    print("=" * 60)
    
    cache_hits = sum(1 for r in results if r['cache_hit'])
    avg_latency = sum(r['memory_retrieval_ms'] for r in results) / len(results)
    cache_latencies = [r['memory_retrieval_ms'] for r in results if r['cache_hit']]
    full_search_latencies = [r['memory_retrieval_ms'] for r in results if not r['cache_hit']]
    
    print(f"Total messages: {len(results)}")
    print(f"Cache hits: {cache_hits}")
    print(f"Cache hit rate: {(cache_hits/len(results)*100):.1f}%")
    print(f"Average latency: {avg_latency:.1f}ms")
    
    if cache_latencies:
        print(f"Cache hit latency: {sum(cache_latencies)/len(cache_latencies):.1f}ms")
    if full_search_latencies:
        print(f"Full search latency: {sum(full_search_latencies)/len(full_search_latencies):.1f}ms")
    
    # Performance assessment
    if avg_latency < 50:
        print("\n✅ EXCELLENT: Average latency under 50ms")
    elif avg_latency < 100:
        print("\n⚠️  GOOD: Average latency under 100ms")
    else:
        print("\n❌ NEEDS IMPROVEMENT: Average latency over 100ms")
    
    return results

def test_cache_warming():
    """Test cache warming with multiple conversations"""
    print("\n" + "=" * 60)
    print("🔥 CACHE WARMING TEST")
    print("=" * 60)
    
    cache = ConversationCache()
    user_id = "test-user-warming"
    
    # Create multiple conversation contexts
    conversations = []
    for i in range(3):
        conv_id = str(uuid.uuid4())
        conversations.append(conv_id)
        
        # Warm up each conversation
        test_memories = [
            MemoryNode(f"Conversation {i+1} context memory A", confidence=0.8),
            MemoryNode(f"Conversation {i+1} context memory B", confidence=0.7),
        ]
        
        for j, memory in enumerate(test_memories):
            memory.id = f"conv-{i}-memory-{j}"
        
        cache.update_conversation_context(
            conv_id,
            "assistant", 
            f"Context for conversation {i+1}",
            test_memories
        )
    
    # Test retrieval from warmed cache
    total_retrieval_time = 0
    for i, conv_id in enumerate(conversations):
        start_time = time.time()
        cached_memories = cache.get_cached_memories(conv_id)
        end_time = time.time()
        
        retrieval_time = (end_time - start_time) * 1000
        total_retrieval_time += retrieval_time
        
        print(f"Conversation {i+1}: {retrieval_time:.1f}ms ({len(cached_memories)} memories)")
    
    avg_retrieval = total_retrieval_time / len(conversations)
    print(f"\nAverage warmed cache retrieval: {avg_retrieval:.1f}ms")
    
    return avg_retrieval

def main():
    """Run comprehensive integrated cache tests"""
    print("Starting Integrated Conversation Cache Tests")
    print("Testing the complete chat flow with caching enabled\n")
    
    # Test conversation flow
    conversation_results = test_conversation_flow()
    
    # Test cache warming
    warming_latency = test_cache_warming()
    
    # Final assessment
    print("\n" + "=" * 60)
    print("🎯 INTEGRATED SYSTEM ASSESSMENT")
    print("=" * 60)
    
    avg_conv_latency = sum(r['memory_retrieval_ms'] for r in conversation_results) / len(conversation_results)
    cache_hit_rate = sum(1 for r in conversation_results if r['cache_hit']) / len(conversation_results) * 100
    
    print(f"Conversation flow average latency: {avg_conv_latency:.1f}ms")
    print(f"Cache hit rate: {cache_hit_rate:.1f}%")
    print(f"Cache warming performance: {warming_latency:.1f}ms")
    
    # Overall success criteria
    success_criteria = [
        avg_conv_latency < 100,  # Sub-100ms average
        cache_hit_rate > 40,     # At least 40% cache hits
        warming_latency < 10     # Sub-10ms warmed cache
    ]
    
    if all(success_criteria):
        print("\n✅ INTEGRATED CACHE SYSTEM: FULLY OPERATIONAL")
        print("   - Performance targets met")
        print("   - Cache hit rate acceptable") 
        print("   - Cache warming effective")
    else:
        print("\n⚠️  INTEGRATED CACHE SYSTEM: PARTIALLY OPERATIONAL")
        print("   - Some performance targets missed")
        print("   - System functional but could be optimized")
    
    print(f"\n📈 Performance Improvement Summary:")
    print(f"   Target: <20ms retrieval for active conversations")
    print(f"   Achieved: {avg_conv_latency:.1f}ms average")
    print(f"   Cache effectiveness: {cache_hit_rate:.1f}% hit rate")

if __name__ == "__main__":
    main()