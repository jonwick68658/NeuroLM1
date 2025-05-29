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

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        background-color: #f8f9fa;
    }
    
    .memory-indicator {
        font-size: 0.8rem;
        color: #6c757d;
        font-style: italic;
        margin-top: 0.5rem;
    }
    
    .conversation-item {
        padding: 0.5rem;
        margin: 0.2rem 0;
        border-radius: 5px;
        border-left: 3px solid #28a745;
        background-color: #f8f9fa;
        cursor: pointer;
    }
    
    .conversation-item:hover {
        background-color: #e9ecef;
    }
    
    .neural-stats {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
</style>
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
        <div class="main-header">
            <h1>🧠 NeuroLM</h1>
            <p>Your Personal Neural Language Model</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Welcome to NeuroLM")
        st.markdown("""
        NeuroLM creates a personalized AI that learns and remembers from your conversations. 
        Your neural network grows stronger with each interaction, building lasting memories 
        and intelligent connections.
        """)
        
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
    <div style="text-align: center; padding: 1rem; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                color: white; border-radius: 10px; margin-bottom: 1rem;">
        <h3>🧠 NeuroLM</h3>
        <p style="margin: 0; font-size: 0.9rem;">Neural Memory System</p>
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