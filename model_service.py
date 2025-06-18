"""
Model Service for OpenRouter integration
"""
import requests
import os
from typing import List, Dict, Optional
import asyncio
import httpx

class ModelService:
    """Service for managing OpenRouter AI models and chat completions"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self._models_cache = None
        self.default_models = [
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "description": "Fast and efficient model for general chat"},
            {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "description": "Google's latest fast model"},
            {"id": "google/gemini-2.5-flash-lite-preview-06-17", "name": "Gemini 2.5 Flash Lite", "description": "1M+ context window"}
        ]
    
    def get_models(self) -> List[Dict]:
        """Get available models from OpenRouter"""
        if self._models_cache:
            return self._models_cache
        
        try:
            if not self.api_key:
                return self.default_models
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{self.base_url}/models", headers=headers, timeout=10)
            
            if response.status_code == 200:
                models_data = response.json()
                models = []
                
                for model in models_data.get("data", []):
                    models.append({
                        "id": model.get("id", ""),
                        "name": model.get("name", model.get("id", "Unknown")),
                        "description": model.get("description", "")
                    })
                
                self._models_cache = models
                return models
            else:
                return self.default_models
                
        except Exception as e:
            print(f"Error fetching models: {e}")
            return self.default_models
    
    async def chat_completion(self, messages: List[Dict], model: str = "openai/gpt-4o-mini") -> str:
        """Generate chat completion using OpenRouter API"""
        
        if not self.api_key:
            raise Exception("OpenRouter API key is required for chat completions")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://neurolm.replit.app",
            "X-Title": "NeuroLM Chat"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"API error: {response.status_code} - {response.text}")
                    
        except Exception as e:
            raise Exception(f"Chat completion failed: {str(e)}")
    
    def search_models(self, query: str) -> List[Dict]:
        """Search models by name or description"""
        models = self.get_models()
        query_lower = query.lower()
        
        filtered = []
        for model in models:
            if (query_lower in model.get("name", "").lower() or 
                query_lower in model.get("description", "").lower()):
                filtered.append(model)
        
        return filtered
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict]:
        """Get model details by ID"""
        models = self.get_models()
        for model in models:
            if model.get("id") == model_id:
                return model
        return None