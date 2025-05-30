import streamlit as st
from model_service import ModelService
from typing import Optional, Dict, List
import time

class ModelSelector:
    """Simple searchable dropdown for OpenRouter models"""
    
    def __init__(self):
        self.model_service = ModelService()
    
    def _format_model_display(self, model: Dict) -> str:
        """Format model for dropdown display"""
        provider = model.get('provider', 'Unknown')
        name = model.get('name', 'Unknown Model')
        context = model.get('context_length', 0)
        
        context_str = f"{context:,}k" if context > 0 else "N/A"
        return f"{provider} | {name} ({context_str} tokens)"
    
    def _save_user_preference(self, user_id: str, model_id: str):
        """Save user's model preference"""
        try:
            # You can integrate with your Neo4j memory system here
            # For now, we'll use session state
            if 'user_model_preferences' not in st.session_state:
                st.session_state.user_model_preferences = {}
            st.session_state.user_model_preferences[user_id] = model_id
        except Exception as e:
            st.error(f"Failed to save preference: {str(e)}")
    
    def _get_user_preference(self, user_id: str) -> Optional[str]:
        """Get user's saved model preference"""
        try:
            prefs = st.session_state.get('user_model_preferences', {})
            return prefs.get(user_id)
        except Exception:
            return None
    
    def render_selector(self, user_id: str) -> str:
        """Render the complete model selector interface"""
        st.sidebar.markdown("### 🤖 AI Model Selection")
        
        # Get user's preference or default
        user_preference = self._get_user_preference(user_id)
        current_model = st.session_state.get('selected_model', user_preference or 'openai/gpt-4o-mini')
        
        # Refresh button
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.markdown("**Available Models**")
        with col2:
            if st.button("🔄", help="Refresh models", key="refresh_models"):
                models = self.model_service.get_models(force_refresh=True)
                st.rerun()
        
        # Load models
        with st.sidebar:
            with st.spinner("Loading models..."):
                models = self.model_service.get_models()
        
        if not models:
            st.sidebar.error("Failed to load models. Please check your OpenRouter API key.")
            return current_model
        
        # Search functionality
        search_query = st.sidebar.text_input(
            "🔍 Search models",
            placeholder="Search by name, provider, or description...",
            key="model_search"
        )
        
        # Filter controls
        with st.sidebar.expander("🎛️ Filters", expanded=False):
            # Provider filter
            providers = sorted(set(model['provider'] for model in models))
            selected_provider = st.selectbox(
                "Provider",
                ["All"] + providers,
                key="provider_filter"
            )
            
            # Capability filters
            vision_only = st.checkbox("Vision capable only", key="vision_filter")
            
            # Context length filter
            min_context = st.slider(
                "Minimum context length",
                0, 1000000, 0, 50000,
                format="%d tokens",
                key="context_filter"
            )
        
        # Apply filters
        filtered_models = self.model_service.search_models(search_query, models)
        
        if selected_provider != "All":
            filtered_models = [m for m in filtered_models if m['provider'] == selected_provider]
        
        if vision_only:
            filtered_models = [m for m in filtered_models if "image" in m.get('input_modalities', [])]
        
        if min_context > 0:
            filtered_models = [m for m in filtered_models if m.get('context_length', 0) >= min_context]
        
        # Display results count
        st.sidebar.markdown(f"*Showing {len(filtered_models)} of {len(models)} models*")
        
        # Current selection display
        current_model_info = self.model_service.get_model_by_id(current_model)
        if current_model_info:
            st.sidebar.success(f"**Current**: {current_model_info['name']}")
        
        # Model categories for better organization
        if not search_query and selected_provider == "All" and not vision_only and min_context == 0:
            # Show categorized view
            categories = self.model_service.get_model_categories(filtered_models)
            
            for category, category_models in categories.items():
                if category_models:
                    with st.sidebar.expander(f"📂 {category} ({len(category_models)})", expanded=(category == "Featured")):
                        for i, model in enumerate(category_models):
                            is_selected = (model['id'] == current_model)
                            if self._render_model_card(model, is_selected, user_id, f"{category}_{i}"):
                                st.session_state.selected_model = model['id']
                                self._save_user_preference(user_id, model['id'])
                                st.rerun()
        else:
            # Show filtered list
            if filtered_models:
                for i, model in enumerate(filtered_models):
                    is_selected = (model['id'] == current_model)
                    if self._render_model_card(model, is_selected, user_id, f"filtered_{i}"):
                        st.session_state.selected_model = model['id']
                        self._save_user_preference(user_id, model['id'])
                        st.rerun()
            else:
                st.sidebar.warning("No models match your search criteria.")
        
        return st.session_state.get('selected_model', current_model)
    
    def get_selected_model(self, user_id: str) -> str:
        """Get the currently selected model ID"""
        user_preference = self._get_user_preference(user_id)
        return st.session_state.get('selected_model', user_preference or 'openai/gpt-4o-mini')