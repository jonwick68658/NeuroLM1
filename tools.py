"""
Tool definitions for OpenRouter tool calling functionality
"""
import json
from typing import List, Dict, Optional
from intelligent_memory import IntelligentMemorySystem

# Initialize memory system
memory_system = IntelligentMemorySystem()

# Tool function implementations
async def search_memory_tool(query: str, user_id: str, limit: int = 3) -> str:
    """Search user's memory for relevant information"""
    try:
        result = await memory_system.retrieve_memory(
            query=query,
            user_id=user_id,
            conversation_id=None,
            limit=limit
        )
        return result
    except Exception as e:
        return f"Memory search failed: {str(e)}"

def get_current_time() -> str:
    """Get the current date and time"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Tool definitions for OpenRouter
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search the user's personal memory for relevant information, facts, or previous conversations",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant memories"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memory results to return (default: 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# Tool mapping for execution
TOOL_MAPPING = {
    "search_memory": search_memory_tool,
    "get_current_time": get_current_time
}

async def execute_tool(tool_name: str, arguments: Dict, user_id: str = None) -> str:
    """Execute a tool function with given arguments"""
    if tool_name not in TOOL_MAPPING:
        return f"Unknown tool: {tool_name}"
    
    try:
        tool_func = TOOL_MAPPING[tool_name]
        
        # Add user_id for memory-related tools
        if tool_name == "search_memory" and user_id:
            arguments["user_id"] = user_id
        
        # Execute tool (handle both sync and async functions)
        if hasattr(tool_func, '__call__'):
            if hasattr(tool_func, '__await__'):
                result = await tool_func(**arguments)
            else:
                result = tool_func(**arguments)
        
        return str(result)
    except Exception as e:
        return f"Tool execution failed: {str(e)}"