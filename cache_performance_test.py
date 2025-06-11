#!/usr/bin/env python3
"""
Performance testing script for conversational context caching system.
Tests cache hit/miss scenarios and measures latency improvements.
"""

import requests
import json
import time
import uuid
from typing import Dict, List

class CachePerformanceTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.user_session = None
        self.conversation_id = None
        
    def login_test_user(self) -> bool:
        """Login as test user or create one if needed"""
        try:
            # Try to login
            login_data = {
                "username": "testuser",
                "password": "testpass123"
            }
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            if response.status_code == 200:
                print("✓ Logged in successfully")
                return True
            else:
                print("⚠ Login failed, user may not exist")
                return False
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def create_conversation(self) -> str:
        """Create a new conversation for testing"""
        try:
            conv_data = {
                "title": "Cache Performance Test",
                "topic": "Performance Testing",
                "sub_topic": "Memory Caching"
            }
            response = self.session.post(f"{self.base_url}/api/conversations/new", json=conv_data)
            
            if response.status_code == 200:
                conv_id = response.json().get("id")
                print(f"✓ Created test conversation: {conv_id}")
                return conv_id
            else:
                print(f"⚠ Failed to create conversation: {response.status_code}")
                return None
        except Exception as e:
            print(f"✗ Conversation creation error: {e}")
            return None
    
    def send_chat_message(self, message: str, conversation_id: str = None) -> Dict:
        """Send chat message and measure response time"""
        start_time = time.time()
        
        try:
            chat_data = {
                "message": message,
                "model": "gpt-4o-mini",
                "conversation_id": conversation_id
            }
            response = self.session.post(f"{self.base_url}/api/chat", json=chat_data)
            
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "latency_ms": latency_ms,
                    "response": result.get("response", ""),
                    "memory_stored": result.get("memory_stored", False),
                    "context_used": result.get("context_used", 0),
                    "conversation_id": result.get("conversation_id")
                }
            else:
                return {
                    "success": False,
                    "latency_ms": latency_ms,
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            return {
                "success": False,
                "latency_ms": latency_ms,
                "error": str(e)
            }
    
    def get_cache_stats(self) -> Dict:
        """Get current cache statistics"""
        try:
            response = self.session.get(f"{self.base_url}/api/cache/stats")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def run_cache_performance_test(self) -> Dict:
        """Run comprehensive cache performance test"""
        print("🚀 Starting Conversation Cache Performance Test")
        print("=" * 60)
        
        results = {
            "test_messages": [],
            "performance_metrics": {},
            "cache_stats": {}
        }
        
        # Login first
        if not self.login_test_user():
            print("✗ Cannot proceed without authentication")
            return results
        
        # Create test conversation
        conversation_id = self.create_conversation()
        if not conversation_id:
            print("✗ Cannot proceed without conversation")
            return results
        
        # Test sequence: First message (cache miss)
        print("\n📝 Test 1: Initial message (expected cache miss)")
        msg1_result = self.send_chat_message(
            "Hello, I'm testing the conversation caching system. Can you help me understand how memory retrieval works?",
            conversation_id
        )
        results["test_messages"].append(msg1_result)
        print(f"   Latency: {msg1_result['latency_ms']:.1f}ms")
        print(f"   Success: {msg1_result['success']}")
        
        # Test sequence: Follow-up message (potential cache hit)
        print("\n📝 Test 2: Follow-up message (potential cache hit)")
        msg2_result = self.send_chat_message(
            "Can you elaborate on the memory system's performance improvements?",
            conversation_id
        )
        results["test_messages"].append(msg2_result)
        print(f"   Latency: {msg2_result['latency_ms']:.1f}ms")
        print(f"   Success: {msg2_result['success']}")
        
        # Test sequence: Related message (should use cached context)
        print("\n📝 Test 3: Related context message (should use cache)")
        msg3_result = self.send_chat_message(
            "What about the conversation drift detection you mentioned?",
            conversation_id
        )
        results["test_messages"].append(msg3_result)
        print(f"   Latency: {msg3_result['latency_ms']:.1f}ms")
        print(f"   Success: {msg3_result['success']}")
        
        # Test sequence: Topic shift (should trigger cache refresh)
        print("\n📝 Test 4: Topic shift message (may trigger cache refresh)")
        msg4_result = self.send_chat_message(
            "Let's change topics completely. Tell me about quantum computing and its applications in machine learning.",
            conversation_id
        )
        results["test_messages"].append(msg4_result)
        print(f"   Latency: {msg4_result['latency_ms']:.1f}ms")
        print(f"   Success: {msg4_result['success']}")
        
        # Get final cache statistics
        cache_stats = self.get_cache_stats()
        results["cache_stats"] = cache_stats
        
        # Calculate performance metrics
        successful_messages = [msg for msg in results["test_messages"] if msg["success"]]
        if successful_messages:
            latencies = [msg["latency_ms"] for msg in successful_messages]
            results["performance_metrics"] = {
                "total_messages": len(results["test_messages"]),
                "successful_messages": len(successful_messages),
                "average_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "cache_enabled": True
            }
        
        return results
    
    def print_test_summary(self, results: Dict):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("📊 CONVERSATION CACHE PERFORMANCE RESULTS")
        print("="*60)
        
        metrics = results.get("performance_metrics", {})
        cache_stats = results.get("cache_stats", {})
        
        if metrics:
            print(f"Total Messages Sent: {metrics['total_messages']}")
            print(f"Successful Messages: {metrics['successful_messages']}")
            print(f"Average Latency: {metrics['average_latency_ms']:.1f}ms")
            print(f"Best Performance: {metrics['min_latency_ms']:.1f}ms")
            print(f"Worst Performance: {metrics['max_latency_ms']:.1f}ms")
            
            # Performance analysis
            avg_latency = metrics['average_latency_ms']
            if avg_latency < 50:
                print("🎯 EXCELLENT: Sub-50ms average latency achieved!")
            elif avg_latency < 100:
                print("✅ GOOD: Sub-100ms average latency achieved!")
            elif avg_latency < 200:
                print("⚠️  ACCEPTABLE: Sub-200ms latency, room for improvement")
            else:
                print("❌ NEEDS IMPROVEMENT: >200ms latency detected")
        
        print(f"\nCache Status: {cache_stats.get('cache_statistics', {}).get('cache_type', 'unknown')}")
        print(f"Cache Connected: {cache_stats.get('cache_statistics', {}).get('connected', False)}")
        
        # Detailed message analysis
        print(f"\n📋 Message-by-Message Analysis:")
        for i, msg in enumerate(results.get("test_messages", []), 1):
            status = "✅" if msg["success"] else "❌"
            print(f"   {status} Message {i}: {msg['latency_ms']:.1f}ms")
            if not msg["success"]:
                print(f"      Error: {msg.get('error', 'Unknown error')}")


def main():
    """Run the cache performance test"""
    tester = CachePerformanceTester()
    
    print("Conversation Cache Performance Test")
    print("This test measures memory retrieval latency improvements")
    print("Target: <20ms retrieval for cached conversations\n")
    
    results = tester.run_cache_performance_test()
    tester.print_test_summary(results)
    
    # Save results to file
    with open("cache_performance_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to cache_performance_results.json")


if __name__ == "__main__":
    main()