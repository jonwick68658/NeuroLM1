import streamlit as st
import logging
from datetime import datetime
import pytz
from memory import Neo4jMemory
from utils import validate_environment, format_memory_context
import openai
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize OpenRouter client
client = openai.OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Page configuration
st.set_page_config(
    page_title="NeuroLM - Your Personal Neural Language Model",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced cosmic neural theme styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600&display=swap');
    
    /* Global cosmic theme */
    .stApp {
        background: radial-gradient(ellipse at bottom, #1B2735 0%, #090A0F 100%);
        color: #ffffff;
    }
    
    /* Animated starfield background */
    .cosmic-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            radial-gradient(2px 2px at 20px 30px, #eee, transparent),
            radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
            radial-gradient(1px 1px at 90px 40px, #fff, transparent),
            radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent),
            radial-gradient(2px 2px at 160px 30px, #ddd, transparent);
        background-repeat: repeat;
        background-size: 200px 100px;
        animation: sparkle 20s linear infinite;
        pointer-events: none;
        z-index: -1;
    }
    
    @keyframes sparkle {
        from { transform: translateY(0px); }
        to { transform: translateY(-100px); }
    }
    
    /* Neural glow effects */
    @keyframes neuralPulse {
        0%, 100% { box-shadow: 0 0 20px rgba(255, 107, 157, 0.3); }
        50% { box-shadow: 0 0 40px rgba(255, 107, 157, 0.6), 0 0 60px rgba(0, 212, 255, 0.4); }
    }
    
    @keyframes synapticSpark {
        0%, 100% { opacity: 0.6; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.1); }
    }
    
    /* Cinematic welcome screen */
    .neural-welcome {
        position: relative;
        text-align: center;
        padding: 4rem 2rem;
        background: radial-gradient(ellipse at center, rgba(26, 26, 46, 0.9) 0%, rgba(9, 10, 15, 0.95) 100%);
        border-radius: 20px;
        border: 1px solid rgba(255, 107, 157, 0.2);
        margin: 2rem 0;
        animation: neuralPulse 4s ease-in-out infinite;
        backdrop-filter: blur(10px);
    }
    
    .neural-brain {
        font-size: 4rem;
        margin-bottom: 1rem;
        animation: synapticSpark 3s ease-in-out infinite;
        filter: drop-shadow(0 0 20px rgba(255, 107, 157, 0.8));
    }
    
    .neural-title {
        font-family: 'Orbitron', monospace;
        font-size: 3.5rem;
        font-weight: 900;
        background: linear-gradient(45deg, #ff6b9d, #00d4ff, #c44569, #667eea);
        background-size: 400% 400%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradientShift 6s ease infinite;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 30px rgba(255, 107, 157, 0.5);
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .neural-subtitle {
        font-family: 'Exo 2', sans-serif;
        font-size: 1.2rem;
        color: #b8c6db;
        font-weight: 300;
        letter-spacing: 2px;
        opacity: 0.9;
    }
    
    /* Enhanced main headers */
    .main-header {
        text-align: center;
        padding: 2rem 1rem;
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.8) 0%, rgba(22, 33, 62, 0.9) 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 107, 157, 0.3);
        backdrop-filter: blur(10px);
        animation: neuralPulse 8s ease-in-out infinite;
    }
    
    .main-header h1, .main-header h2 {
        font-family: 'Orbitron', monospace;
        background: linear-gradient(45deg, #ff6b9d, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    /* Sidebar neural styling */
    .sidebar-neural {
        background: linear-gradient(180deg, rgba(26, 26, 46, 0.9) 0%, rgba(16, 21, 62, 0.95) 100%);
        border: 1px solid rgba(255, 107, 157, 0.2);
        border-radius: 15px;
        padding: 1rem;
        margin-bottom: 1rem;
        animation: neuralPulse 10s ease-in-out infinite;
    }
    
    .sidebar-neural h3 {
        font-family: 'Orbitron', monospace;
        background: linear-gradient(45deg, #ff6b9d, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 0;
    }
    
    /* Enhanced conversation items */
    .conversation-item {
        padding: 0.8rem;
        margin: 0.3rem 0;
        border-radius: 10px;
        background: linear-gradient(135deg, rgba(255, 107, 157, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%);
        border-left: 3px solid #ff6b9d;
        cursor: pointer;
        transition: all 0.3s ease;
        backdrop-filter: blur(5px);
    }
    
    .conversation-item:hover {
        background: linear-gradient(135deg, rgba(255, 107, 157, 0.2) 0%, rgba(0, 212, 255, 0.1) 100%);
        transform: translateX(5px);
        box-shadow: 0 5px 15px rgba(255, 107, 157, 0.3);
    }
    
    /* Neural stats display */
    .neural-stats {
        background: linear-gradient(135deg, rgba(255, 107, 157, 0.2) 0%, rgba(0, 212, 255, 0.1) 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        border: 1px solid rgba(255, 107, 157, 0.3);
        backdrop-filter: blur(10px);
        animation: synapticSpark 5s ease-in-out infinite;
    }
    
    .neural-stats h4 {
        font-family: 'Orbitron', monospace;
        color: #ff6b9d;
        margin-bottom: 0.8rem;
        text-align: center;
    }
    
    /* Memory indicators */
    .memory-indicator {
        font-size: 0.8rem;
        color: #b8c6db;
        font-style: italic;
        margin-top: 0.5rem;
        padding: 0.3rem 0.6rem;
        background: rgba(255, 107, 157, 0.1);
        border-radius: 15px;
        border-left: 2px solid #ff6b9d;
    }
    
    /* Enhanced form styling */
    .stTextInput > div > div > input {
        background: rgba(26, 26, 46, 0.8) !important;
        border: 1px solid rgba(255, 107, 157, 0.3) !important;
        color: white !important;
        border-radius: 10px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #ff6b9d !important;
        box-shadow: 0 0 10px rgba(255, 107, 157, 0.5) !important;
    }
    
    /* Button enhancements */
    .stButton > button {
        background: linear-gradient(45deg, #ff6b9d, #c44569) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        font-family: 'Exo 2', sans-serif !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #c44569, #ff6b9d) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(255, 107, 157, 0.4) !important;
    }
    
    /* Chat message styling */
    .stChatMessage {
        background: rgba(26, 26, 46, 0.6) !important;
        border: 1px solid rgba(255, 107, 157, 0.2) !important;
        border-radius: 15px !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* Metrics styling */
    .metric-container {
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.8) 0%, rgba(22, 33, 62, 0.9) 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border: 1px solid rgba(255, 107, 157, 0.3);
        text-align: center;
        backdrop-filter: blur(10px);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>

<div class="cosmic-bg"></div>
""", unsafe_allow_html=True)

def init_memory():
    """Initialize memory system with error handling"""
    try:
        if "memory" not in st.session_state:
            validate_environment()
            st.session_state.memory = Neo4jMemory()
            
            # Run schema repair on first initialization
            if "schema_repaired" not in st.session_state:
                with st.spinner("Optimizing neural network..."):
                    st.session_state.memory.repair_schema()
                    st.session_state.schema_repaired = True
                    
        return st.session_state.memory
    except Exception as e:
        st.error(f"Failed to initialize NeuroLM memory system: {str(e)}")
        st.stop()

def user_authentication():
    """Enhanced user authentication system"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_id = None
    
    if not st.session_state.authenticated:
        st.markdown("""
        <div class="neural-welcome">
            <div class="neural-brain">🧠</div>
            <h1 class="neural-title">NeuroLM</h1>
            <p class="neural-subtitle">Your Personal Neural Language Model</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; padding: 2rem; background: rgba(26, 26, 46, 0.6); 
                    border-radius: 15px; border: 1px solid rgba(255, 107, 157, 0.2); 
                    backdrop-filter: blur(10px); margin: 1rem 0;">
            <h3 style="color: #ff6b9d; font-family: 'Orbitron', monospace; margin-bottom: 1rem;">
                Welcome to the Future of Personal AI
            </h3>
            <p style="color: #b8c6db; font-family: 'Exo 2', sans-serif; line-height: 1.6;">
                NeuroLM creates a personalized AI that learns and remembers from your conversations.<br>
                Your neural network grows stronger with each interaction, building lasting memories<br>
                and intelligent connections that evolve with your unique knowledge patterns.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.subheader("Sign In")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Enter NeuroLM")
            
            if login_button:
                # For MVP, use environment variables, later expand to database
                if (username == os.getenv("APP_USERNAME") and 
                    password == os.getenv("APP_PASSWORD")):
                    st.session_state.authenticated = True
                    st.session_state.user_id = f"user_{username}"
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
        
        st.markdown("---")
        st.markdown("**NeuroLM Features:**")
        st.markdown("• Persistent memory across all conversations")
        st.markdown("• Intelligent topic detection and organization")  
        st.markdown("• Associative memory linking related discussions")
        st.markdown("• Biomemetic learning that strengthens with use")
        st.stop()

def get_conversation_history(memory, user_id, limit=15):
    """Get recent and frequently accessed conversations"""
    try:
        with memory.driver.session() as session:
            # Get recent conversations grouped by session/topic
            recent_conversations = session.run("""
            MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory {role: 'user'})
            WHERE m.timestamp >= datetime() - duration('P7D')
            RETURN m.content as content, m.timestamp as timestamp, 
                   coalesce(m.access_count, 0) as access_count
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """, user_id=user_id, limit=limit)
            
            return [{"content": r["content"][:60] + "..." if len(r["content"]) > 60 else r["content"],
                    "timestamp": r["timestamp"], 
                    "access_count": r["access_count"]} for r in recent_conversations]
    except Exception as e:
        logging.error(f"Failed to get conversation history: {str(e)}")
        return []

def render_sidebar(memory, user_id):
    """Render enhanced sidebar with conversation history"""
    st.sidebar.markdown("""
    <div class="sidebar-neural">
        <div class="neural-brain" style="font-size: 2rem; text-align: center; margin-bottom: 0.5rem;">🧠</div>
        <h3>NeuroLM</h3>
        <p style="margin: 0; font-size: 0.9rem; text-align: center; color: #b8c6db; font-family: 'Exo 2', sans-serif;">Neural Memory System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio("", ["💬 Chat", "🧠 Memory Analytics", "⚙️ Settings"], key="nav_radio")
    
    st.sidebar.markdown("---")
    
    # Recent Conversations
    st.sidebar.markdown("### Recent Conversations")
    conversations = get_conversation_history(memory, user_id)
    
    if conversations:
        for i, conv in enumerate(conversations[:8]):
            access_indicator = "🔥" if conv["access_count"] > 3 else "💭"
            st.sidebar.markdown(f"""
            <div class="conversation-item" onclick="streamlit.setComponentValue('selected_conv', {i})">
                {access_indicator} {conv["content"]}<br>
                <small style="color: #6c757d;">{conv["timestamp"].strftime('%m/%d %H:%M') if hasattr(conv["timestamp"], 'strftime') else 'Recent'}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.sidebar.info("Start a conversation to see your memory history here.")
    
    # Quick Neural Stats
    try:
        stats = memory.get_memory_stats(user_id)
        st.sidebar.markdown(f"""
        <div class="neural-stats">
            <h4>Neural Status</h4>
            <p>💾 {stats.get('total_memories', 0)} Memories</p>
            <p>🔗 {stats.get('total_connections', 0)} Connections</p>
            <p>🧩 {stats.get('total_topics', 0)} Topics</p>
        </div>
        """, unsafe_allow_html=True)
    except:
        pass
    
    return page

def chat_interface(memory, user_id):
    """Main chat interface"""
    st.markdown("""
    <div class="main-header">
        <h2>💬 Chat with NeuroLM</h2>
        <p>Your personal AI that learns and remembers</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "memory_context" in message:
                st.markdown(f'<div class="memory-indicator">💡 Drew from {len(message["memory_context"])} memories</div>', 
                           unsafe_allow_html=True)
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("🧠 Accessing neural memory..."):
                try:
                    # Store user message and get relevant memories
                    memory.store_chat(user_id, "user", prompt)
                    relevant_memories = memory.get_relevant_memories(prompt, user_id, limit=7)
                    
                    # Create context
                    context = format_memory_context(relevant_memories, max_context_length=2000)
                    
                    # Generate response
                    messages = [
                        {"role": "system", "content": f"""You are NeuroLM, a personal AI assistant with neural memory capabilities. 
                        You have access to the user's conversation history and can form lasting memories.
                        
                        Context from neural memory:
                        {context}
                        
                        Use this context naturally in your responses. Be helpful, intelligent, and personable."""},
                        {"role": "user", "content": prompt}
                    ]
                    
                    response = client.chat.completions.create(
                        model="openai/gpt-4o-mini-2024-07-18",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    assistant_response = response.choices[0].message.content
                    
                    # Store assistant response
                    memory.store_chat(user_id, "assistant", assistant_response)
                    
                    # Display response
                    st.markdown(assistant_response)
                    
                    # Show memory context indicator
                    if relevant_memories:
                        st.markdown(f'<div class="memory-indicator">💡 Drew from {len(relevant_memories)} memories</div>', 
                                   unsafe_allow_html=True)
                    
                    # Add to session history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": assistant_response,
                        "memory_context": relevant_memories
                    })
                    
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")

def memory_analytics_page(memory, user_id):
    """Dedicated memory analytics page"""
    st.markdown("""
    <div class="main-header">
        <h2>🧠 Memory Analytics</h2>
        <p>Explore your neural network growth and connections</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        stats = memory.get_memory_stats(user_id)
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Memories", stats.get('total_memories', 0))
        with col2:
            st.metric("Neural Connections", stats.get('total_connections', 0))
        with col3:
            st.metric("Active Topics", stats.get('total_topics', 0))
        with col4:
            st.metric("Strong Memories", stats.get('strong_memories', 0))
        
        st.markdown("---")
        
        # Detailed analytics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Memory Distribution")
            st.info(f"Average Confidence: {stats.get('avg_confidence', 0):.1%}")
            st.info(f"Total Accesses: {stats.get('total_accesses', 0)}")
            st.info(f"Memory Strength: {stats.get('avg_connection_strength', 0):.1%}")
            
        with col2:
            st.subheader("Top Topics")
            top_topics = stats.get('top_topics', [])
            if top_topics:
                for topic in top_topics[:5]:
                    st.write(f"• **{topic['name']}** ({topic['count']} mentions)")
            else:
                st.info("Start conversations to see topic analysis")
        
        # Memory management
        st.markdown("---")
        st.subheader("Memory Management")
        
        if st.button("Run Memory Optimization"):
            with st.spinner("Optimizing neural connections..."):
                memory.reinforce_memories(user_id)
                st.success("Memory optimization completed!")
                st.rerun()
                
    except Exception as e:
        st.error(f"Unable to load memory analytics: {str(e)}")

def settings_page():
    """Settings and configuration page"""
    st.markdown("""
    <div class="main-header">
        <h2>⚙️ Settings</h2>
        <p>Configure your NeuroLM experience</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Account Information")
    st.info(f"User ID: {st.session_state.user_id}")
    
    st.subheader("Memory Preferences")
    memory_retention = st.slider("Memory Retention Strength", 0.1, 1.0, 0.8, 0.1)
    topic_sensitivity = st.slider("Topic Detection Sensitivity", 0.1, 1.0, 0.6, 0.1)
    
    st.subheader("System Information")
    st.info("NeuroLM v1.0 - Neural Memory System")
    st.info("Connected to Neo4j Aura Database")
    
    if st.button("Sign Out"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.rerun()

def main():
    """Main application"""
    # User authentication
    user_authentication()
    
    # Initialize memory system
    memory = init_memory()
    user_id = st.session_state.user_id
    
    # Render sidebar and get current page
    current_page = render_sidebar(memory, user_id)
    
    # Render appropriate page
    if current_page == "💬 Chat":
        chat_interface(memory, user_id)
    elif current_page == "🧠 Memory Analytics":
        memory_analytics_page(memory, user_id)
    elif current_page == "⚙️ Settings":
        settings_page()

if __name__ == "__main__":
    main()