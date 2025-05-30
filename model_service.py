import requests
import os
import streamlit as st
from typing import List, Dict, Optional
import time
import json

class ModelService:
    """Service for fetching and managing OpenRouter models"""
    
    def __init__(self):
        self.api_url = "https://openrouter.ai/api/v1/models"
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.cache_key = "openrouter_models_cache"
        self.cache_timestamp_key = "openrouter_models_timestamp"
        self.cache_duration = 3600  # 1 hour in seconds
        
    def _get_headers(self):
        """Get API headers for OpenRouter requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "NeuroLM/1.0"
        }
    
    def _is_cache_valid(self):
        """Check if cached data is still valid"""
        if self.cache_key not in st.session_state or self.cache_timestamp_key not in st.session_state:
            return False
        
        cache_time = st.session_state[self.cache_timestamp_key]
        return (time.time() - cache_time) < self.cache_duration
    
    def _get_cached_models(self):
        """Get models from cache if valid"""
        if self._is_cache_valid():
            return st.session_state[self.cache_key]
        return None
    
    def _cache_models(self, models):
        """Cache models data"""
        st.session_state[self.cache_key] = models
        st.session_state[self.cache_timestamp_key] = time.time()
    
    def _get_fallback_models(self):
        """Return essential models as fallback"""
        return [
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "description": "Fast and efficient GPT-4 variant optimized for speed",
                "provider": "OpenAI",
                "context_length": 128000,
                "pricing": {"prompt": "0.00000015", "completion": "0.0000006"},
                "input_modalities": ["text"],
                "output_modalities": ["text"]
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "description": "Most capable GPT-4 model with multimodal capabilities",
                "provider": "OpenAI", 
                "context_length": 128000,
                "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                "input_modalities": ["text", "image"],
                "output_modalities": ["text"]
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Anthropic's most intelligent model with advanced reasoning",
                "provider": "Anthropic",
                "context_length": 200000,
                "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                "input_modalities": ["text", "image"],
                "output_modalities": ["text"]
            },
            {
                "id": "google/gemini-pro-1.5",
                "name": "Gemini Pro 1.5",
                "description": "Google's advanced multimodal AI with large context window",
                "provider": "Google",
                "context_length": 1000000,
                "pricing": {"prompt": "0.00000125", "completion": "0.000005"},
                "input_modalities": ["text", "image"],
                "output_modalities": ["text"]
            },
            {
                "id": "meta-llama/llama-3.1-405b-instruct",
                "name": "Llama 3.1 405B Instruct",
                "description": "Meta's largest and most capable open-source model",
                "provider": "Meta",
                "context_length": 131072,
                "pricing": {"prompt": "0.000005", "completion": "0.000015"},
                "input_modalities": ["text"],
                "output_modalities": ["text"]
            }
        ]
    
    def _format_model(self, model_data):
        """Format raw model data into standardized structure"""
        try:
            # Extract provider name from model ID
            provider = model_data.get("id", "").split("/")[0].title()
            if not provider:
                provider = "Unknown"
            
            # Get pricing info
            pricing = model_data.get("pricing", {})
            prompt_cost = pricing.get("prompt", "0")
            completion_cost = pricing.get("completion", "0")
            
            # Get architecture info
            architecture = model_data.get("architecture", {})
            input_modalities = architecture.get("input_modalities", ["text"])
            output_modalities = architecture.get("output_modalities", ["text"])
            
            return {
                "id": model_data.get("id", ""),
                "name": model_data.get("name", ""),
                "description": model_data.get("description", "")[:200],  # Limit description length
                "provider": provider,
                "context_length": model_data.get("context_length", 0),
                "pricing": {
                    "prompt": prompt_cost,
                    "completion": completion_cost
                },
                "input_modalities": input_modalities,
                "output_modalities": output_modalities,
                "created": model_data.get("created", 0),
                "supported_parameters": model_data.get("supported_parameters", [])
            }
        except Exception as e:
            # Return None for malformed models
            return None
    
    def get_models(self, force_refresh=False):
        """Fetch all available models from OpenRouter API"""
        # Check cache first unless force refresh
        if not force_refresh:
            cached = self._get_cached_models()
            if cached:
                return cached
        
        try:
            if not self.api_key:
                st.warning("OpenRouter API key not found. Using fallback models.")
                return self._get_fallback_models()
            
            # Make API request
            response = requests.get(self.api_url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            data = response.json()
            raw_models = data.get("data", [])
            
            # Format and filter models
            formatted_models = []
            for model in raw_models:
                formatted = self._format_model(model)
                if formatted and formatted["id"] and formatted["name"]:
                    formatted_models.append(formatted)
            
            # Sort models by provider and name
            formatted_models.sort(key=lambda x: (x["provider"], x["name"]))
            
            # Cache the results
            self._cache_models(formatted_models)
            
            return formatted_models
            
        except requests.RequestException as e:
            st.error(f"Failed to fetch models from OpenRouter: {str(e)}")
            return self._get_fallback_models()
        except Exception as e:
            st.error(f"Error processing models: {str(e)}")
            return self._get_fallback_models()
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict]:
        """Get specific model information by ID"""
        models = self.get_models()
        return next((model for model in models if model["id"] == model_id), None)
    
    def search_models(self, query: str, models: List[Dict]) -> List[Dict]:
        """Search models by name, description, or provider"""
        if not query:
            return models
        
        query = query.lower()
        filtered = []
        
        for model in models:
            # Search in name, description, and provider
            searchable_text = f"{model['name']} {model['description']} {model['provider']}".lower()
            if query in searchable_text:
                filtered.append(model)
        
        return filtered
    
    def get_models_by_provider(self, provider: str, models: List[Dict]) -> List[Dict]:
        """Filter models by provider"""
        return [model for model in models if model["provider"].lower() == provider.lower()]
    
    def get_model_categories(self, models: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize models for better organization"""
        categories = {
            "Featured": [],
            "Fast & Affordable": [],
            "Balanced": [],
            "Premium": [],
            "Specialized": []
        }
        
        featured_ids = [
            "openai/gpt-4o-mini",
            "openai/gpt-4o", 
            "anthropic/claude-3.5-sonnet",
            "google/gemini-pro-1.5",
            "meta-llama/llama-3.1-405b-instruct"
        ]
        
        for model in models:
            # Featured models
            if model["id"] in featured_ids:
                categories["Featured"].append(model)
            
            # Categorize by cost (rough estimates)
            try:
                prompt_cost = float(model["pricing"]["prompt"])
                
                if prompt_cost < 0.000001:  # Very cheap
                    categories["Fast & Affordable"].append(model)
                elif prompt_cost < 0.000003:  # Moderate
                    categories["Balanced"].append(model)
                else:  # Expensive
                    categories["Premium"].append(model)
                    
            except (ValueError, KeyError):
                categories["Specialized"].append(model)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}