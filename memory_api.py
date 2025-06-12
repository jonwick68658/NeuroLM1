from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional
import datetime
import os
from memory import MemorySystem
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create router for API endpoints
router = APIRouter()

# Create a global memory system instance
memory_system = MemorySystem()

class MemoryRequest(BaseModel):
    content: str
    confidence: Optional[float] = 0.8
    user_id: Optional[str] = None
    
class MemoryResponse(BaseModel):
    id: str
    content: str
    confidence: float
    category: str
    timestamp: str
    
class RetrieveMemoryRequest(BaseModel):
    query: str
    context: Optional[str] = None
    depth: Optional[int] = 5
    
class MemoryOperationRequest(BaseModel):
    memory_id: str
    
class MemoryOperationResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict] = None
    
class MemoryDecayRequest(BaseModel):
    force_decay: Optional[bool] = False
    
@router.post("/memorize/", response_model=MemoryResponse)
async def memorize_content(memory_request: MemoryRequest):
    """
    Add new content to memory
    """
    try:
        memory_id = memory_system.add_memory(
            content=memory_request.content,
            confidence=memory_request.confidence or 0.8,
            user_id=memory_request.user_id
        )
        
        memory_node = memory_system.get_memory_node(memory_id)
        if not memory_node:
            raise HTTPException(status_code=404, detail="Memory creation failed")
            
        return MemoryResponse(
            id=memory_node.id,
            content=memory_node.content[:1000],
            confidence=memory_node.confidence,
            category=memory_node.category,
            timestamp=memory_node.timestamp.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.post("/retrieve/", response_model=List[MemoryResponse])
async def retrieve_memories(retrieve_request: RetrieveMemoryRequest):
    """
    Retrieve relevant memories based on query
    """
    try:
        memories = memory_system.retrieve_memories(
            query=retrieve_request.query,
            context=retrieve_request.context or "",
            depth=retrieve_request.depth or 5
        )
        
        # Convert to response format
        memory_responses = []
        for memory_node in memories:
            memory_responses.append(MemoryResponse(
                id=memory_node.id,
                content=memory_node.content[:1000],
                confidence=memory_node.confidence,
                category=memory_node.category,
                timestamp=memory_node.timestamp.isoformat()
            ))
            
        return memory_responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.put("/enhance/{memory_id}")
async def enhance_memory(memory_id: str):
    """
    Enhance a memory by reinforcing it
    """
    try:
        memory = memory_system.get_memory_node(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
            
        memory_system.reinforce_memory(memory_id, reinforcement=1.0)
        
        return {
            "success": True,
            "message": "Memory enhanced successfully",
            "details": {
                "memory_id": memory_id,
                "new_confidence": memory.confidence
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.put("/decay/")
async def decay_memories(decay_request: MemoryDecayRequest):
    """
    Trigger memory decay process
    """
    try:
        memory_system.decay_memories(force_decay=decay_request.force_decay or False)
        return {
            "success": True,
            "message": "Memory decay process initiated",
            "details": {
                "force_decay": decay_request.force_decay
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))        
      
@router.post("/forget/{memory_id}")
async def forget_memory(memory_id: str):
    """
    Permanently remove a memory from the system
    """
    try:
        memory_system.forget_memory(memory_id)
        return {
            "success": True,
            "message": "Memory successfully forgotten"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    try:
        return {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))