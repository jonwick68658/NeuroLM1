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

# NeuroLM Professional Dark Theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global Dark Theme */
.stApp {
    background-color: #0d1117;
    color: #e6edf3;
}

.main > div {
    background-color: #0d1117;
}

/* Header Styling */
.neuro-header {
    background: linear-gradient(135deg, #4c9aff 0%, #7b68ee 50%, #ff6b9d 100%);
    padding: 3rem 2rem;
    border-radius: 20px;
    margin-bottom: 2rem;
    text-align: center;
    color: white;
    position: relative;
    overflow: hidden;
}

.neuro-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.1);
    backdrop-filter: blur(10px);
}

.neuro-title {
    font-family: 'Inter', sans-serif;
    font-size: 4rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -2px;
    position: relative;
    z-index: 1;
    text-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.neuro-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 1.4rem;
    font-weight: 300;
    margin: 0.5rem 0 0 0;
    opacity: 0.95;
    position: relative;
    z-index: 1;
}

/* Login Page Styling */
.login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    background: #161b22;
    border-radius: 16px;
    border: 1px solid #30363d;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

/* Input Styling */
.stTextInput > div > div > input {
    background-color: #21262d !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.75rem 1rem !important;
}

.stTextInput > div > div > input:focus {
    border-color: #4c9aff !important;
    box-shadow: 0 0 0 3px rgba(76, 154, 255, 0.1) !important;
}

/* Button Styling */
.stButton > button {
    background: linear-gradient(135deg, #4c9aff 0%, #7b68ee 100%) !important;
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    padding: 0.75rem 2rem !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(76, 154, 255, 0.4) !important;
}

/* Navigation Buttons */
.nav-button {
    background: #21262d !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    padding: 0.75rem 1.5rem !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    margin-right: 0.5rem !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
}

.nav-button:hover {
    background: #30363d !important;
    border-color: #4c9aff !important;
}

.nav-button.active {
    background: linear-gradient(135deg, #4c9aff 0%, #7b68ee 100%) !important;
    color: white !important;
    border: none !important;
}

/* Sidebar Styling */
.sidebar-section {
    background-color: #161b22;
    padding: 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border: 1px solid #30363d;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}

.sidebar-title {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 1rem;
    font-size: 1.1rem;
}

.topic-item {
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    color: #8b949e;
    margin: 0.5rem 0;
    padding: 0.5rem;
    background-color: #21262d;
    border-radius: 6px;
    border-left: 3px solid #4c9aff;
}

.chat-item {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: #e6edf3;
    padding: 0.75rem;
    background-color: #21262d;
    border-radius: 8px;
    margin-bottom: 0.75rem;
    cursor: pointer;
    border: 1px solid #30363d;
    transition: all 0.3s ease;
}

.chat-item:hover {
    background-color: #30363d;
    border-color: #4c9aff;
}

/* Chat Message Styling */
.stChatMessage {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 12px !important;
}

/* Success/Error Messages */
.stSuccess {
    background-color: #1a472a !important;
    color: #4cc9f0 !important;
    border: 1px solid #46954a !important;
}

.stError {
    background-color: #490008 !important;
    color: #ff6b9d !important;
    border: 1px solid #da1e37 !important;
}

.stWarning {
    background-color: #4d2d00 !important;
    color: #ffa500 !important;
    border: 1px solid #ff8500 !important;
}

/* Metrics */
.metric-container {
    background-color: #161b22;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #30363d;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

def check_login():
    """Handle user login"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        # NeuroLM Login Header
        st.markdown("""
        <div class="neuro-header">
            <h1 class="neuro-title">NeuroLM</h1>
            <p class="neuro-subtitle">Your Personal Neural Language Model</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login Container
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown("### Access Your Neural Network")
        st.markdown("Enter your credentials to continue")
        
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        
        if st.button("Connect to NeuroLM"):
            app_username = os.getenv("APP_USERNAME")
            app_password = os.getenv("APP_PASSWORD")
            
            if username == app_username and password == app_password:
                st.session_state.authenticated = True
                st.success("Neural connection established")
                st.rerun()
            else:
                st.error("Invalid credentials. Access denied.")
        
        st.markdown('</div>', unsafe_allow_html=True)
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
            
            if recent_chats and isinstance(recent_chats, list):
                for chat in recent_chats[:5]:
                    # Handle both string and dict formats
                    if isinstance(chat, dict):
                        content = chat.get("content", "")
                        role = chat.get("role", "user")
                        role_icon = "🤖" if role == "assistant" else "👤"
                    else:
                        content = str(chat)
                        role_icon = "💬"
                    
                    # Clean the content and create preview
                    if content and len(content.strip()) > 0:
                        # Remove any code or query content
                        if not any(keyword in content.lower() for keyword in ["match", "return", "session.run", "cypher", "neo4j"]):
                            preview = content[:50] + "..." if len(content) > 50 else content
                            preview = preview.replace('\n', ' ').strip()
                            if preview:
                                st.markdown(f'<div class="chat-item">{role_icon} {preview}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="topic-item">No conversations yet</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Popular topics
            stats = memory.get_memory_stats(DEFAULT_USER)
            
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-title">Most Discussed Topics</div>', unsafe_allow_html=True)
            
            if stats and stats.get("top_topics"):
                for topic, count in stats["top_topics"][:5]:
                    if isinstance(topic, str) and len(topic.strip()) > 0:
                        # Filter out any code or query strings
                        if not any(keyword in topic.lower() for keyword in ["match", "return", "session", "cypher"]):
                            st.markdown(f'<div class="topic-item">{topic} ({count})</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="topic-item">No topics identified yet</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-title">Neural Network</div>', unsafe_allow_html=True)
            st.markdown('<div class="topic-item">Connecting...</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)



def main():
    if check_login():
        # Navigation
        if "page" not in st.session_state:
            st.session_state.page = "chat"
        
        # Header
        st.markdown("""
        <div class="neuro-header">
            <h1 class="neuro-title">NeuroLM</h1>
            <p class="neuro-subtitle">Your Personal Neural Language Model</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Top navigation bar with menu
        nav_col1, nav_col2 = st.columns([9, 1])
        
        with nav_col2:
            menu_option = st.selectbox("", ["⋮", "Disconnect"], key="top_menu", label_visibility="collapsed")
            if menu_option == "Disconnect":
                st.session_state.authenticated = False
                st.rerun()
        
        st.markdown("---")
        
        # Sidebar content
        with st.sidebar:
            chat_history_sidebar()
        
        # Main chat interface
        chat_interface()

def chat_interface():
    """Main chat interface"""
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

You are an intelligent AI assistant designed to act as the user's second brain."""
                
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