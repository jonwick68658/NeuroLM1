import streamlit as st
from model_service import ModelService
from typing import Optional, Dict, List

class SimpleModelSelector:
    """Simple searchable dropdown for OpenRouter models"""
    
    def __init__(self):
        self.model_service = ModelService()
    
    def _save_user_preference(self, user_id: str, model_id: str):
        """Save user's model preference"""
        try:
            if 'user_model_preferences' not in st.session_state:
                st.session_state.user_model_preferences = {}
            st.session_state.user_model_preferences[user_id] = model_id
        except Exception:
            pass
    
    def _get_user_preference(self, user_id: str) -> Optional[str]:
        """Get user's saved model preference"""
        try:
            prefs = st.session_state.get('user_model_preferences', {})
            return prefs.get(user_id)
        except Exception:
            return None
    
    def render_selector(self, user_id: str) -> str:
        """Render simple model selector dropdown"""
        # Load models
        models = self.model_service.get_models()
        
        if not models:
            return "openai/gpt-4o-mini"
        
        # Create model options for dropdown
        model_options = {}
        model_display_names = []
        
        for model in models:
            name = model.get('name', 'Unknown')
            model_id = model.get('id', '')
            
            if model_id and name:
                model_options[name] = model_id
                model_display_names.append(name)
        
        # Get current selection
        user_preference = self._get_user_preference(user_id)
        current_model = st.session_state.get('selected_model', user_preference or 'openai/gpt-4o-mini')
        
        # Simple dropdown
        if model_display_names:
            # Find current index
            current_index = 0
            for i, name in enumerate(model_display_names):
                if model_options[name] == current_model:
                    current_index = i
                    break
            
            selected_name = st.selectbox(
                "AI Model",
                options=model_display_names,
                index=current_index
            )
            
            selected_model = model_options[selected_name]
            if selected_model != current_model:
                st.session_state.selected_model = selected_model
                self._save_user_preference(user_id, selected_model)
            
            return selected_model
        
        return "openai/gpt-4o-mini"
    
    def get_selected_model(self, user_id: str) -> str:
        """Get the currently selected model ID"""
        user_preference = self._get_user_preference(user_id)
        return st.session_state.get('selected_model', user_preference or 'openai/gpt-4o-mini')