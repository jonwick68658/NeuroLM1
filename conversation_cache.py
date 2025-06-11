"""
Conversational Context Caching System
====================================

High-performance conversation memory caching to reduce retrieval latency
from 119ms to <20ms for active conversations.
"""

import redis
import json
import time
import hashlib
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import os
from memory import MemoryNode


class ConversationCache:
    """
    Redis-based conversation context cache for ultra-fast memory retrieval
    """
    
    def __init__(self):
        """Initialize Redis connection and cache configuration"""
        # Redis connection with fallback to localhost
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        try:
            # Use direct Redis client initialization as suggested
            self.redis_client: Optional[redis.Redis] = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            # Test connection
            self.redis_client.ping()
        except Exception:
            # Fallback to in-memory storage if Redis unavailable
            self.redis_client: Optional[redis.Redis] = None
            self._memory_cache: Dict[str, Dict] = {}
            
        # Cache configuration
        self.default_ttl = 7200  # 2 hours
        self.max_messages_per_conversation = 15
        self.max_promoted_memories = 10
        self.cache_size_limit = 51200  # 50KB per conversation
        
    def _get_cache_key(self, conversation_id: str) -> str:
        """Generate cache key for conversation"""
        return f"conv_cache:{conversation_id}"
    
    def _get_cache_data(self, key: str) -> Optional[Dict]:
        """Get data from cache (Redis or in-memory fallback)"""
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                if data and isinstance(data, str):
                    return json.loads(data)
                return None
            else:
                # In-memory fallback
                if key in self._memory_cache:
                    item = self._memory_cache[key]
                    # Check TTL for in-memory cache
                    if time.time() - item['created'] < self.default_ttl:
                        return item['data']
                    else:
                        del self._memory_cache[key]
                return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def _set_cache_data(self, key: str, data: Dict, ttl: Optional[int] = None) -> bool:
        """Set data in cache (Redis or in-memory fallback)"""
        try:
            ttl = ttl or self.default_ttl
            serialized_data = json.dumps(data)
            
            # Check size limit
            if len(serialized_data) > self.cache_size_limit:
                print(f"Cache data too large: {len(serialized_data)} bytes")
                return False
            
            if self.redis_client:
                result = self.redis_client.setex(key, ttl, serialized_data)
                return bool(result)
            else:
                # In-memory fallback
                self._memory_cache[key] = {
                    'data': data,
                    'created': time.time()
                }
                return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def _delete_cache_data(self, key: str) -> bool:
        """Delete data from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                return bool(self._memory_cache.pop(key, None))
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def get_conversation_context(self, conversation_id: str) -> Optional[Dict]:
        """
        Retrieve conversation context from cache
        Returns: Dict with messages, promoted_memories, topic_context
        """
        cache_key = self._get_cache_key(conversation_id)
        context = self._get_cache_data(cache_key)
        
        if context:
            # Update last accessed timestamp
            context['last_accessed'] = datetime.now().isoformat()
            self._set_cache_data(cache_key, context)
            
        return context
    
    def update_conversation_context(self, conversation_id: str, message_role: str, 
                                  message_content: str, promoted_memories: Optional[List[MemoryNode]] = None) -> bool:
        """
        Update conversation context with new message and optionally promote memories
        """
        cache_key = self._get_cache_key(conversation_id)
        context = self._get_cache_data(cache_key)
        
        # Initialize context if doesn't exist
        if not context:
            context = {
                "conversation_id": conversation_id,
                "messages": [],
                "promoted_memories": [],
                "topic_context": {
                    "current_topic": None,
                    "coherence_score": 1.0
                },
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            }
        
        # Add new message
        new_message = {
            "role": message_role,
            "content": message_content,
            "timestamp": datetime.now().isoformat()
        }
        context["messages"].append(new_message)
        
        # Maintain message limit (keep most recent)
        if len(context["messages"]) > self.max_messages_per_conversation:
            context["messages"] = context["messages"][-self.max_messages_per_conversation:]
        
        # Update promoted memories if provided
        if promoted_memories:
            for memory in promoted_memories:
                memory_data = {
                    "id": memory.id,
                    "content": memory.content,
                    "confidence": memory.confidence,
                    "timestamp": memory.timestamp.isoformat() if hasattr(memory.timestamp, 'isoformat') else str(memory.timestamp)
                }
                
                # Check if memory already promoted
                existing_ids = [m["id"] for m in context["promoted_memories"]]
                if memory.id not in existing_ids:
                    context["promoted_memories"].append(memory_data)
            
            # Maintain promoted memory limit (keep highest confidence)
            if len(context["promoted_memories"]) > self.max_promoted_memories:
                context["promoted_memories"].sort(key=lambda x: x["confidence"], reverse=True)
                context["promoted_memories"] = context["promoted_memories"][:self.max_promoted_memories]
        
        # Update access time
        context["last_accessed"] = datetime.now().isoformat()
        
        return self._set_cache_data(cache_key, context)
    
    def get_cached_memories(self, conversation_id: str) -> List[MemoryNode]:
        """
        Get promoted memories from conversation cache as MemoryNode objects
        """
        context = self.get_conversation_context(conversation_id)
        if not context or not context.get("promoted_memories"):
            return []
        
        memories = []
        for memory_data in context["promoted_memories"]:
            # Reconstruct MemoryNode from cached data
            try:
                timestamp_str = memory_data.get("timestamp", "")
                if timestamp_str:
                    # Try to parse the timestamp
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()
                
                memory = MemoryNode(
                    content=memory_data["content"],
                    confidence=memory_data["confidence"],
                    timestamp=timestamp
                )
                memory.id = memory_data["id"]
                memories.append(memory)
            except Exception as e:
                print(f"Error reconstructing memory from cache: {e}")
                continue
        
        return memories
    
    def detect_conversation_drift(self, conversation_id: str, new_message: str) -> float:
        """
        Detect if conversation topic has drifted significantly
        Returns: coherence score (0.0 = total drift, 1.0 = perfect continuity)
        """
        context = self.get_conversation_context(conversation_id)
        if not context or len(context["messages"]) < 2:
            return 1.0  # No drift if insufficient history
        
        # Simple keyword-based drift detection
        recent_messages = context["messages"][-3:]  # Last 3 messages
        recent_content = " ".join([msg["content"] for msg in recent_messages])
        
        # Calculate word overlap as proxy for topic continuity
        recent_words = set(recent_content.lower().split())
        new_words = set(new_message.lower().split())
        
        if len(recent_words) == 0:
            return 1.0
        
        overlap = len(recent_words & new_words)
        coherence = overlap / len(recent_words | new_words) if len(recent_words | new_words) > 0 else 1.0
        
        # Update topic context
        if context:
            context["topic_context"]["coherence_score"] = coherence
            self._set_cache_data(self._get_cache_key(conversation_id), context)
        
        return coherence
    
    def should_refresh_cache(self, conversation_id: str, coherence_threshold: float = 0.3) -> bool:
        """
        Determine if cache should be refreshed due to topic drift
        """
        context = self.get_conversation_context(conversation_id)
        if not context:
            return True
        
        coherence = context.get("topic_context", {}).get("coherence_score", 1.0)
        return coherence < coherence_threshold
    
    def invalidate_conversation_cache(self, conversation_id: str) -> bool:
        """
        Manually invalidate conversation cache
        """
        cache_key = self._get_cache_key(conversation_id)
        return self._delete_cache_data(cache_key)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics
        """
        try:
            if self.redis_client:
                info = self.redis_client.info()
                # Handle Redis info response safely
                memory_usage = "unknown"
                keyspace_hits = 0
                keyspace_misses = 0
                
                if isinstance(info, dict):
                    memory_usage = info.get("used_memory_human", "unknown")
                    keyspace_hits = info.get("keyspace_hits", 0)
                    keyspace_misses = info.get("keyspace_misses", 0)
                
                return {
                    "cache_type": "redis",
                    "connected": True,
                    "memory_usage": memory_usage,
                    "keyspace_hits": keyspace_hits,
                    "keyspace_misses": keyspace_misses
                }
            else:
                return {
                    "cache_type": "in_memory",
                    "connected": True,
                    "cached_conversations": len(self._memory_cache),
                    "memory_usage": "unknown"
                }
        except Exception as e:
            return {
                "cache_type": "unknown",
                "connected": False,
                "error": str(e)
            }
    
    def cleanup_expired_conversations(self) -> int:
        """
        Clean up expired conversation caches (for in-memory fallback)
        Returns: number of cleaned up conversations
        """
        if self.redis_client:
            return 0  # Redis handles TTL automatically
        
        cleaned = 0
        current_time = time.time()
        expired_keys = []
        
        for key, item in self._memory_cache.items():
            if current_time - item['created'] > self.default_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._memory_cache[key]
            cleaned += 1
        
        return cleaned
    
    def warm_conversation_cache(self, conversation_id: str, recent_messages: List[Dict]) -> bool:
        """
        Warm cache with recent conversation messages from authentic data
        """
        if not recent_messages:
            return False
        
        try:
            # Initialize cache context with real conversation data
            cache_key = self._get_cache_key(conversation_id)
            context = {
                "conversation_id": conversation_id,
                "messages": [],
                "promoted_memories": [],
                "topic_context": {
                    "current_topic": None,
                    "coherence_score": 1.0
                },
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            }
            
            # Add recent messages to cache
            for msg in recent_messages:
                context["messages"].append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"]
                })
            
            # Maintain message limit
            if len(context["messages"]) > self.max_messages_per_conversation:
                context["messages"] = context["messages"][-self.max_messages_per_conversation:]
            
            return self._set_cache_data(cache_key, context)
        except Exception as e:
            print(f"Cache warming error: {e}")
            return False
    
    def get_active_conversations(self) -> List[str]:
        """
        Get list of currently cached conversation IDs
        """
        if self.redis_client:
            try:
                # Get all cache keys matching our pattern
                pattern = "conv_cache:*"
                keys = self.redis_client.keys(pattern)
                return [key.replace("conv_cache:", "") for key in keys]
            except Exception:
                return []
        else:
            # Extract conversation IDs from in-memory cache
            return [key.replace("conv_cache:", "") for key in self._memory_cache.keys()]
    
    def prioritize_conversation_cache(self, conversation_id: str) -> bool:
        """
        Mark a conversation as high priority for caching (extend TTL)
        """
        cache_key = self._get_cache_key(conversation_id)
        context = self._get_cache_data(cache_key)
        
        if context:
            # Extend TTL for high-priority conversations
            extended_ttl = self.default_ttl * 2  # 4 hours instead of 2
            context["last_accessed"] = datetime.now().isoformat()
            context["priority"] = "high"
            return self._set_cache_data(cache_key, context, extended_ttl)
        
        return False