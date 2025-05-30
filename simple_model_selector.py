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
        st.sidebar.markdown("### 🤖 AI Model")
        
        # Load models
        with st.spinner("Loading models..."):
            models = self.model_service.get_models()
        
        if not models:
            st.sidebar.error("Failed to load models")
            return "openai/gpt-4o-mini"
        
        # Sort models alphabetically by provider then name
        sorted_models = sorted(models, key=lambda x: (x.get('provider', ''), x.get('name', '')))
        
        # Create model options for dropdown
        model_options = {}
        model_display_names = []
        
        for model in sorted_models:
            provider = model.get('provider', 'Unknown')
            name = model.get('name', 'Unknown')
            model_id = model.get('id', '')
            
            if model_id and name:
                display_name = f"{provider} - {name}"
                model_options[display_name] = model_id
                model_display_names.append(display_name)
        
        # Get current selection
        user_preference = self._get_user_preference(user_id)
        current_model = st.session_state.get('selected_model', user_preference or 'openai/gpt-4o-mini')
        
        # Find current display name
        current_display = None
        for display_name, model_id in model_options.items():
            if model_id == current_model:
                current_display = display_name
                break
        
        if current_display is None and model_display_names:
            current_display = model_display_names[0]
            current_model = model_options[current_display]
        
        # Search functionality
        search_query = st.sidebar.text_input(
            "Search models",
            placeholder="Type to search...",
            key="model_search",
            label_visibility="collapsed"
        )
        
        # Filter models based on search
        if search_query:
            filtered_options = {
                display: model_id for display, model_id in model_options.items()
                if search_query.lower() in display.lower()
            }
            filtered_display_names = list(filtered_options.keys())
        else:
            filtered_options = model_options
            filtered_display_names = model_display_names
        
        # Model selection dropdown
        if filtered_display_names:
            # Ensure current selection is in the filtered list
            if current_display not in filtered_display_names and filtered_display_names:
                current_display = filtered_display_names[0]
                current_model = filtered_options[current_display]
            
            selected_display = st.sidebar.selectbox(
                "Model",
                options=filtered_display_names,
                index=filtered_display_names.index(current_display) if current_display in filtered_display_names else 0,
                key="model_selectbox",
                label_visibility="collapsed"
            )
            
            # Update selected model
            if selected_display in filtered_options:
                selected_model = filtered_options[selected_display]
                if selected_model != current_model:
                    st.session_state.selected_model = selected_model
                    self._save_user_preference(user_id, selected_model)
                    st.rerun()
                current_model = selected_model
        
        else:
            st.sidebar.warning("No models match your search")
        
        # Show current model info in a compact way
        current_model_info = self.model_service.get_model_by_id(current_model)
        if current_model_info:
            context = current_model_info.get('context_length', 0)
            if context > 0:
                st.sidebar.caption(f"Context: {context:,} tokens")
        
        return current_model
    
    def get_selected_model(self, user_id: str) -> str:
        """Get the currently selected model ID"""
        user_preference = self._get_user_preference(user_id)
        return st.session_state.get('selected_model', user_preference or 'openai/gpt-4o-mini')