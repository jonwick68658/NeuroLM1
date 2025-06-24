"""
Tool Handler for OpenRouter Tool Calling
Implements the agentic loop for tool execution
"""
import json
import asyncio
from typing import List, Dict, Optional, Any
from model_service import ModelService
from tools import AVAILABLE_TOOLS, execute_tool

class ToolHandler:
    """Handles tool calling with agentic loop"""
    
    def __init__(self):
        self.model_service = ModelService()
        self.max_iterations = 10  # Prevent infinite loops
    
    async def chat_with_tools(self, messages: List[Dict], user_id: str, model: str = "openai/gpt-4o-mini") -> Dict:
        """
        Complete chat with tool calling support using agentic loop
        Returns final response and execution details
        """
        iteration_count = 0
        tool_calls_made = []
        current_messages = messages.copy()
        
        while iteration_count < self.max_iterations:
            iteration_count += 1
            
            try:
                # Make API call with tools
                response = await self.model_service.chat_completion_with_tools(
                    messages=current_messages,
                    model=model,
                    tools=AVAILABLE_TOOLS
                )
                
                # Add assistant response to messages
                current_messages.append(response)
                
                # Check if tool calls were made
                if response.get('tool_calls'):
                    # Process each tool call
                    for tool_call in response['tool_calls']:
                        tool_name = tool_call['function']['name']
                        tool_args = json.loads(tool_call['function']['arguments'])
                        
                        # Execute the tool
                        tool_result = await execute_tool(tool_name, tool_args, user_id)
                        
                        # Record tool call
                        tool_calls_made.append({
                            'name': tool_name,
                            'arguments': tool_args,
                            'result': tool_result
                        })
                        
                        # Add tool result to messages
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call['id'],
                            "name": tool_name,
                            "content": str(tool_result)
                        })
                    
                    # Continue loop to get final response
                    continue
                else:
                    # No more tool calls, return final response
                    return {
                        'success': True,
                        'response': response.get('content', ''),
                        'tool_calls_made': tool_calls_made,
                        'iterations': iteration_count,
                        'messages': current_messages
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'tool_calls_made': tool_calls_made,
                    'iterations': iteration_count
                }
        
        # Max iterations reached
        return {
            'success': False,
            'error': 'Maximum tool calling iterations reached',
            'tool_calls_made': tool_calls_made,
            'iterations': iteration_count
        }
    
    async def simple_tool_call(self, user_message: str, user_id: str, model: str = "openai/gpt-4o-mini") -> Dict:
        """
        Simple single message tool calling
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant with access to tools. Use them when appropriate to provide accurate information."},
            {"role": "user", "content": user_message}
        ]
        
        return await self.chat_with_tools(messages, user_id, model)