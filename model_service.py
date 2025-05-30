"""
Model Service for OpenRouter integration
"""
import requests
import os
from typing import List, Dict, Optional

class ModelService:
    """Service for managing OpenRouter AI models"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self._models_cache = None
    
    def get_models(self) -> List[Dict]:
        """Get available models from OpenRouter"""
        if self._models_cache:
            return self._models_cache
        
        try:
            if not self.api_key:
                # Return basic models if no API key
                return [
                    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                    {"id": "gpt-4", "name": "GPT-4"},
                    {"id": "claude-3-haiku", "name": "Claude 3 Haiku"}
                ]
            
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
                # Fallback models
                return [
                    {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                    {"id": "openai/gpt-4", "name": "GPT-4"},
                    {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku"}
                ]
                
        except Exception as e:
            print(f"Error fetching models: {e}")
            # Return fallback models
            return [
                {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                {"id": "openai/gpt-4", "name": "GPT-4"},
                {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku"}
            ]
    
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