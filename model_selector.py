import streamlit as st
from model_service import ModelService
from typing import Optional, Dict, List
import time

class ModelSelector:
    """UI component for selecting OpenRouter models"""
    
    def __init__(self):
        self.model_service = ModelService()
        
    def _format_cost(self, cost_str: str) -> str:
        """Format cost string for display"""
        try:
            cost = float(cost_str)
            if cost == 0:
                return "Free"
            elif cost < 0.000001:
                return f"${cost * 1000000:.2f}/M"
            else:
                return f"${cost * 1000000:.3f}/M"
        except (ValueError, TypeError):
            return "N/A"
    
    def _get_capability_badges(self, model: Dict) -> str:
        """Generate capability badges for a model"""
        badges = []
        
        # Input modalities
        if "image" in model.get("input_modalities", []):
            badges.append('<span style="background: #4CAF50; padding: 2px 6px; border-radius: 10px; font-size: 0.7rem; margin-right: 4px;">📷 Vision</span>')
        
        # Context length categories
        context = model.get("context_length", 0)
        if context >= 1000000:
            badges.append('<span style="background: #9C27B0; padding: 2px 6px; border-radius: 10px; font-size: 0.7rem; margin-right: 4px;">🧠 1M+ Context</span>')
        elif context >= 200000:
            badges.append('<span style="background: #673AB7; padding: 2px 6px; border-radius: 10px; font-size: 0.7rem; margin-right: 4px;">📚 200K+ Context</span>')
        elif context >= 100000:
            badges.append('<span style="background: #3F51B5; padding: 2px 6px; border-radius: 10px; font-size: 0.7rem; margin-right: 4px;">📖 100K+ Context</span>')
        
        return "".join(badges)
    
    def _render_model_card(self, model: Dict, is_selected: bool, user_id: str, unique_suffix: str = "") -> bool:
        """Render a single model card and return True if selected"""
        bg_color = "#2A2A40" if is_selected else "#1A1A2E"
        border_color = "#BB86FC" if is_selected else "#333350"
        
        with st.container():
            st.markdown(f"""
            <div style="
                background: {bg_color};
                border: 2px solid {border_color};
                border-radius: 12px;
                padding: 16px;
                margin: 8px 0;
                transition: all 0.3s ease;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h4 style="margin: 0; color: {'#BB86FC' if is_selected else '#FFFFFF'}; font-size: 1.1rem;">
                        {model['name']}
                    </h4>
                    <span style="
                        background: {'#6200EA' if model['provider'] == 'OpenAI' else '#1976D2' if model['provider'] == 'Anthropic' else '#4CAF50' if model['provider'] == 'Google' else '#FF5722'};
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 0.75rem;
                        color: white;
                        font-weight: bold;
                    ">
                        {model['provider']}
                    </span>
                </div>
                
                <p style="
                    font-size: 0.85rem;
                    margin: 8px 0;
                    color: #B0B0C0;
                    line-height: 1.4;
                ">
                    {model['description'][:120]}{'...' if len(model['description']) > 120 else ''}
                </p>
                
                <div style="margin: 12px 0;">
                    {self._get_capability_badges(model)}
                </div>
                
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 0.8rem;
                    color: #A0A0B0;
                ">
                    <div>
                        <span style="color: #81C784;">Context: {model['context_length']:,} tokens</span>
                    </div>
                    <div>
                        <span style="color: #FFB74D;">
                            Input: {self._format_cost(model['pricing']['prompt'])} • 
                            Output: {self._format_cost(model['pricing']['completion'])}
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Create columns for selection button
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                button_type = "primary" if is_selected else "secondary"
                button_label = "✓ Selected" if is_selected else "Select"
                
                # Create unique key by adding suffix and hash of model ID
                safe_model_id = model['id'].replace('/', '_').replace('-', '_')
                unique_key = f"select_{safe_model_id}_{unique_suffix}_{hash(model['id']) % 10000}"
                
                if st.button(button_label, key=unique_key, type=button_type, use_container_width=True):
                    return True
            
            return False
    
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