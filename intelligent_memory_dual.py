"""
PostgreSQL Intelligent Memory System
PostgreSQL backend for NeuroLM memory management
"""

import os
import asyncio
from typing import List, Dict, Optional, Union
from enum import Enum
from datetime import datetime, timedelta

# Import memory systems - PostgreSQL only
from postgresql_memory_adapter import PostgreSQLMemorySystem

class MemoryBackend(Enum):
    POSTGRESQL = "postgresql"

class DualIntelligentMemorySystem:
    """PostgreSQL-based intelligent memory system (formerly dual backend)"""
    
    def __init__(self):
        # PostgreSQL backend
        self.backend = MemoryBackend.POSTGRESQL
        self.postgresql_system = PostgreSQLMemorySystem()
        self.active_system = self.postgresql_system
    
    def _determine_backend(self) -> MemoryBackend:
        """Determine which backend to use based on environment"""
        # PostgreSQL backend
        return MemoryBackend.POSTGRESQL
    
    async def store_memory(self, content: str, user_id: str, conversation_id: Optional[str], 
                          message_type: str = "user", message_id: Optional[int] = None) -> Optional[str]:
        """Store memory using PostgreSQL backend"""
        return await self.active_system.store_memory(
            content, user_id, conversation_id, message_type, message_id
        )
    
    async def retrieve_memory(self, query: str, user_id: str, conversation_id: Optional[str], 
                            limit: int = 5) -> str:
        """Retrieve memory using PostgreSQL backend"""
        return await self.active_system.retrieve_memory(
            query, user_id, conversation_id, limit
        )
    
    async def update_memory_quality_score(self, memory_id: str, quality_score: float) -> bool:
        """Update memory quality score using the active backend"""
        return await self.active_system.update_memory_quality_score(memory_id, quality_score)
    
    async def update_human_feedback_by_node_id(self, node_id: str, feedback_score: float, 
                                             feedback_type: str, user_id: str) -> bool:
        """Update human feedback using the active backend"""
        return await self.active_system.update_human_feedback_by_node_id(
            node_id, feedback_score, feedback_type, user_id
        )
    
    async def update_final_quality_score(self, memory_id: str, user_id: str, 
                                       use_message_id: bool = False) -> bool:
        """Update final quality score using PostgreSQL backend"""
        return await self.active_system.update_final_quality_score(memory_id, user_id)
    
    async def get_unscored_memories(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get unscored memories using the active backend"""
        return await self.active_system.get_unscored_memories(user_id, limit)
    
    async def evaluate_response(self, user_query: str, ai_response: str) -> Optional[float]:
        """Evaluate response quality using the active backend"""
        return await self.active_system.evaluate_response(user_query, ai_response)
    
    def calculate_final_quality_score(self, r_t_score: Optional[float], 
                                    h_t_score: Optional[float]) -> Optional[float]:
        """Calculate final quality score using the active backend"""
        return self.active_system.calculate_final_quality_score(r_t_score, h_t_score)
    
    async def score_unscored_memories_background(self, user_id: str) -> Dict[str, int]:
        """Background scoring using the active backend"""
        return await self.active_system.score_unscored_memories_background(user_id)
    
    def get_backend_info(self) -> Dict[str, str]:
        """Get information about the active backend"""
        return {
            "backend": self.backend.value,
            "status": "active",
            "description": f"Using {self.backend.value} for memory storage"
        }
    
    def close(self):
        """Close connections for the active backend"""
        if self.active_system:
            self.active_system.close()