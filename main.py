from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from memory_api import *
from pydantic import BaseModel
import uvicorn
import os
import httpx
from typing import Optional

# Create FastAPI application
app = FastAPI(title="NeuroLM Memory System", version="1.0.0")

# Include memory API routes
app.include_router(router, prefix="/api")

# Serve the chat interface as the main page
@app.get("/")
async def serve_chat():
    """Serve the chat interface"""
    return FileResponse("chat.html")

# Serve the memory management interface
@app.get("/memory")
async def serve_memory():
    """Serve the memory management interface"""
    return FileResponse("index.html")

# Chat models
class ChatMessage(BaseModel):
    message: str
    model: Optional[str] = "gpt-4o-mini"

class ChatResponse(BaseModel):
    response: str
    memory_stored: bool
    context_used: int

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_memory(chat_request: ChatMessage):
    """
    Chat with LLM using memory system for context
    """
    try:
        # Retrieve relevant memories for context
        retrieve_request = RetrieveMemoryRequest(
            query=chat_request.message,
            context=None,
            depth=5
        )
        
        # Get memory system instance
        memory_system = MemorySystem()
        relevant_memories = memory_system.retrieve_memories(
            query=chat_request.message,
            context="",
            depth=5
        )
        
        # Build context from memories
        context = ""
        if relevant_memories:
            context = "\n".join([f"Memory: {mem.content}" for mem in relevant_memories[:3]])
        
        # Call LLM with context
        system_prompt = f"""You are NeuroLM, an AI with access to your memory system. 
        
Relevant memories:
{context}

Respond naturally to the user's message, incorporating relevant memories when helpful."""

        # Store user message in memory
        user_memory_id = memory_system.add_memory(f"User said: {chat_request.message}")
        
        # Create LLM messages with memory context
        system_message = {
            "role": "system",
            "content": f"""You are NeuroLM, an AI with access to your memory system. You function as a thoughtful, supportive friend who speaks honestly and maintains engaging conversations.

Relevant memories from previous conversations:
{context}

Use these memories naturally in your responses when relevant. Be conversational, warm, and helpful."""
        }
        
        user_message = {
            "role": "user", 
            "content": chat_request.message
        }
        
        messages = [system_message, user_message]
        
        # Generate LLM response
        from model_service import ModelService
        model_service = ModelService()
        
        try:
            response_text = await model_service.chat_completion(
                messages=messages,
                model=chat_request.model or "openai/gpt-4o-mini"
            )
        except Exception as e:
            # Fallback response if LLM fails
            response_text = f"I understand your message about '{chat_request.message}'. "
            if relevant_memories:
                response_text += f"This connects to {len(relevant_memories)} memories I have. "
            response_text += "I'm having trouble generating a full response right now."
        
        # Store assistant response in memory
        assistant_memory_id = memory_system.add_memory(f"Assistant responded: {response_text}")
        
        return ChatResponse(
            response=response_text,
            memory_stored=True,
            context_used=len(relevant_memories) if relevant_memories else 0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {"status": "healthy", "service": "NeuroLM Memory System"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)