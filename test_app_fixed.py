import streamlit as st
import openai
import os
from dotenv import load_dotenv
from memory import Neo4jMemory

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
openai_client = openai.OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Initialize memory system
@st.cache_resource
def init_memory():
    try:
        return Neo4jMemory()
    except Exception as e:
        st.error(f"Memory initialization failed: {str(e)}")
        return None

memory = init_memory()
DEFAULT_USER = "default_user"

# NeuroLM Professional Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 15px;
    margin-bottom: 2rem;
    text-align: center;
    color: white;
}

.main-title {
    font-family: 'Inter', sans-serif;
    font-size: 3rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -1px;
}

.main-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 1.2rem;
    font-weight: 300;
    margin: 0.5rem 0 0 0;
    opacity: 0.9;
}

.stTextInput > div > div > input {
    background-color: #1e1e1e;
    color: white;
    border: 1px solid #333;
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
}

.stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 8px;
    border: none;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.sidebar-section {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    border-left: 4px solid #667eea;
}

.sidebar-title {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    color: #333;
    margin-bottom: 0.5rem;
}

.topic-item {
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    color: #666;
    margin: 0.25rem 0;
}

.chat-item {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: #555;
    padding: 0.5rem;
    background-color: #f1f3f4;
    border-radius: 6px;
    margin-bottom: 0.5rem;
    cursor: pointer;
}

.nav-button {
    background: transparent;
    border: 1px solid #ddd;
    color: #666;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-family: 'Inter', sans-serif;
    margin-right: 0.5rem;
    cursor: pointer;
}

.nav-button.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
}
</style>
""", unsafe_allow_html=True)

def check_login():
    """Handle user login"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 Second Brain AI - Login")
        st.write("Please enter your credentials to access your AI assistant.")
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            app_username = os.getenv("APP_USERNAME")
            app_password = os.getenv("APP_PASSWORD")
            
            if username == app_username and password == app_password:
                st.session_state.authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")
        
        return False
    
    return True

def chat_history_sidebar():
    """Display recent conversations and popular topics in sidebar"""
    if memory:
        try:
            # Recent conversation history
            recent_chats = memory.get_conversation_history(DEFAULT_USER, limit=10)
            
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-title">Recent Conversations</div>', unsafe_allow_html=True)
            
            if recent_chats:
                for chat in recent_chats[:5]:
                    preview = chat[:60] + "..." if len(chat) > 60 else chat
                    st.markdown(f'<div class="chat-item">{preview}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="topic-item">No conversations yet</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Popular topics
            stats = memory.get_memory_stats(DEFAULT_USER)
            
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-title">Most Discussed Topics</div>', unsafe_allow_html=True)
            
            if stats.get("top_topics"):
                for topic, count in stats["top_topics"][:5]:
                    st.markdown(f'<div class="topic-item">{topic} ({count})</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="topic-item">No topics identified yet</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-title">Memory System</div>', unsafe_allow_html=True)
            st.markdown('<div class="topic-item">Loading...</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

def neural_settings_page():
    """Neural system settings and controls"""
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">Neural Settings</h1>
        <p class="main-subtitle">Configure your personal neural language model</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Memory System Status")
        
        if memory:
            try:
                stats = memory.get_memory_stats(DEFAULT_USER)
                
                st.metric("Total Memories", stats["total_memories"])
                st.metric("Strong Memories", stats["strong_memories"])
                st.metric("Average Confidence", f"{stats['avg_confidence']*100:.1f}%")
                st.metric("Total Accesses", stats["total_accesses"])
                st.metric("Neural Connections", stats.get("total_links", 0))
                
                st.success("Neural network active")
                
            except Exception as e:
                st.warning(f"Memory system status: {str(e)}")
        else:
            st.info("Session memory mode")
    
    with col2:
        st.subheader("Neural Operations")
        
        if st.button("Strengthen Memory Pathways"):
            if memory:
                with st.spinner("Consolidating neural pathways..."):
                    memory.reinforce_memories(DEFAULT_USER)
                st.success("Memory consolidation complete")
            else:
                st.warning("Neural memory system not available")
        
        if st.button("Clear Memory Cache"):
            if memory:
                if st.checkbox("Confirm memory reset"):
                    memory.clear_user_memories(DEFAULT_USER)
                    st.success("Memory cache cleared")
            else:
                st.warning("Neural memory system not available")
        
        if st.button("Run System Diagnostics"):
            if memory:
                with st.spinner("Running neural diagnostics..."):
                    # Test memory retrieval
                    test_memories = memory.get_relevant_memories("test", DEFAULT_USER, 1)
                    st.info(f"Memory retrieval: {len(test_memories)} results")
                    
                    # Test database connection
                    count = memory.get_memory_count(DEFAULT_USER)
                    st.info(f"Database connection: {count} memories stored")
            else:
                st.warning("Neural memory system not available")

def main():
    if check_login():
        # Navigation
        if "page" not in st.session_state:
            st.session_state.page = "chat"
        
        # Header
        st.markdown("""
        <div class="main-header">
            <h1 class="main-title">NeuroLM</h1>
            <p class="main-subtitle">Your Personal Neural Language Model</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 8])
        
        with col1:
            if st.button("Chat", key="nav_chat"):
                st.session_state.page = "chat"
        
        with col2:
            if st.button("Settings", key="nav_settings"):
                st.session_state.page = "settings"
        
        with col3:
            if st.button("Logout", key="nav_logout"):
                st.session_state.authenticated = False
                st.rerun()
        
        # Sidebar content
        with st.sidebar:
            chat_history_sidebar()
        
        # Page content
        if st.session_state.page == "settings":
            neural_settings_page()
        else:
            chat_interface()

def chat_interface():
    """Main chat interface"""
    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    if prompt := st.chat_input("What would you like to discuss?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Store user message
        if memory:
            try:
                memory.store_chat(DEFAULT_USER, "user", prompt)
            except Exception as e:
                st.warning(f"Memory storage issue: {str(e)}")
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get relevant memories for context
        context = []
        if memory:
            with st.spinner("Retrieving context..."):
                try:
                    context = memory.get_relevant_memories(prompt, DEFAULT_USER)
                    if context:
                        st.success(f"Found {len(context)} relevant memories")
                except Exception as e:
                    st.warning(f"Memory retrieval issue: {str(e)}")
        
        # Get AI response
        with st.chat_message("assistant"):
            try:
                # Build context string
                context_str = "\n\n".join([f"- {mem}" for mem in context]) if context else ""
                enhancements = " with access to your personal knowledge" if context else ""
                
                context_section = f'Relevant Context:\n{context_str}' if context_str else ''
                
                system_prompt = f"""You are NeuroLM, an advanced neural language model{enhancements}.
                
Your capabilities:
1. Recall and reference past conversations naturally
2. Connect information across different discussions
3. Provide thoughtful, contextual responses
4. Build on previous discussions to create continuity

{context_section}

You are an intelligent AI assistant designed to act as the user's second brain.
"""
                
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                message_placeholder = st.empty()
                full_response = ""
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                # Store AI response in Neo4j
                if memory:
                    try:
                        memory.store_chat(DEFAULT_USER, "assistant", full_response)
                    except Exception as e:
                        st.warning(f"Failed to store AI response: {str(e)}")
                        
            except Exception as e:
                st.error(f"AI Response Error: {str(e)}")
                error_response = "I apologize, but I'm experiencing technical difficulties. Please check your OpenRouter API key and try again."
                st.markdown(error_response)
                st.session_state.messages.append({"role": "assistant", "content": error_response})

if __name__ == "__main__":
    main()