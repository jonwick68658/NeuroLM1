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

def get_current_user():
    """Get the current authenticated user ID"""
    return st.session_state.get("user_id", None)

def create_user_account(username, email, password):
    """Create a new user account in Neo4j"""
    if not memory:
        return False, "Memory system not available"
    
    try:
        # Check if username already exists
        existing_username = memory.driver.session().run(
            "MATCH (u:User {username: $username}) RETURN u",
            username=username
        ).single()
        
        if existing_username:
            return False, "Username already exists"
        
        # Check if email already exists
        existing_email = memory.driver.session().run(
            "MATCH (u:User {email: $email}) RETURN u",
            email=email
        ).single()
        
        if existing_email:
            return False, "Email already registered"
        
        # Create new user with hashed password
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        memory.driver.session().run(
            """
            CREATE (u:User {
                id: $user_id,
                username: $username,
                email: $email,
                password_hash: $password_hash,
                created_at: datetime(),
                last_login: datetime()
            })
            """,
            user_id=f"user_{username}",
            username=username,
            email=email,
            password_hash=password_hash
        )
        
        return True, "Account created successfully"
        
    except Exception as e:
        return False, f"Failed to create account: {str(e)}"

def authenticate_user(username, password):
    """Authenticate user login"""
    if not memory:
        return False, "Memory system not available"
    
    try:
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = memory.driver.session().run(
            """
            MATCH (u:User {username: $username, password_hash: $password_hash})
            RETURN u.id as user_id, u.username as username
            """,
            username=username,
            password_hash=password_hash
        ).single()
        
        if user:
            return True, {"user_id": user["user_id"], "username": user["username"]}
        else:
            return False, "Invalid username or password"
            
    except Exception as e:
        return False, f"Authentication failed: {str(e)}"

# Helper functions for real data integration
def get_neural_stats(user_id):
    """Get real neural network statistics from Neo4j"""
    if not memory:
        return {"memory_count": 0, "topic_count": 0, "confidence_pct": 0, "connection_count": 0}
    
    try:
        stats = memory.get_memory_stats(user_id)
        return {
            "memory_count": stats.get("total_memories", 0),
            "topic_count": len(stats.get("top_topics", [])),
            "confidence_pct": int(stats.get("avg_confidence", 0) * 100),
            "connection_count": stats.get("total_links", 0)
        }
    except Exception as e:
        return {"memory_count": 0, "topic_count": 0, "confidence_pct": 0, "connection_count": 0}

def neural_message(content, sender="AI", timestamp=None, sources=None):
    """Custom neural message component replacing default chat"""
    if sender == "AI":
        source_html = ""
        if sources and len(sources) > 0:
            source_list = "\n".join(f"<li style='color: var(--text-secondary); margin: 4px 0;'>{src[:60]}...</li>" for src in sources[:3])
            source_html = f"""
            <div style="margin-top: 12px; font-size: 0.85rem;">
              <div style="display: flex; align-items: center; gap: 8px; color: var(--accent-secondary);">
                <span>Neural Sources</span>
                <span style="background: rgba(127,90,240,0.2); border-radius: 12px; padding: 2px 8px; font-size: 0.75rem;">
                  {len(sources)}
                </span>
              </div>
              <ul style="margin: 8px 0 0 20px; padding: 0; opacity: 0.8;">
                {source_list}
              </ul>
            </div>
            """
        
        timestamp_html = f"""<div style="position: absolute; right: 16px; top: 16px; font-size: 0.75rem; color: var(--text-secondary);">
          {timestamp.strftime('%H:%M') if timestamp else ''}
        </div>""" if timestamp else ""
        
        st.markdown(f"""
        <div class="neural-message" style="border-left: 3px solid var(--accent-secondary); position: relative;">
          {timestamp_html}
          <div style="display: flex; align-items: center; margin-bottom: 12px;">
            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)); border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
              <span style="color: white; font-weight: 800; font-size: 14px;">NL</span>
            </div>
            <div>
              <div style="font-weight: 700; color: var(--accent-secondary);">NeuroLM</div>
              <div style="font-size: 0.85rem; color: var(--text-secondary);">Neural Language Model</div>
            </div>
          </div>
          <div style="color: var(--text-primary); line-height: 1.7; font-size: 1.1rem;">
            {content}
          </div>
          {source_html}
        </div>
        """, unsafe_allow_html=True)
    else:
        timestamp_html = f"""<div style="position: absolute; right: 16px; top: 16px; font-size: 0.75rem; color: var(--text-secondary);">
          {timestamp.strftime('%H:%M') if timestamp else ''}
        </div>""" if timestamp else ""
        
        st.markdown(f"""
        <div class="neural-message" style="border-left: 3px solid #444; position: relative;">
          {timestamp_html}
          <div style="display: flex; align-items: center; margin-bottom: 12px;">
            <div style="width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-right: 12px; background: #333;">
              <span style="color: var(--text-primary); font-weight: 700; font-size: 14px;">U</span>
            </div>
            <div style="font-weight: 700; color: var(--text-primary);">You</div>
          </div>
          <div style="color: var(--text-primary); line-height: 1.7; font-size: 1.1rem;">
            {content}
          </div>
        </div>
        """, unsafe_allow_html=True)

def neural_activity_widget(user_id):
    """Neural activity widget with real data"""
    stats = get_neural_stats(user_id)
    
    st.markdown(f"""
    <div class="neural-stats">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h3 style="margin: 0; color: var(--text-primary);">Neural Activity</h3>
        <div style="font-size: 0.9rem; color: var(--text-secondary);">Real-time</div>
      </div>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value" style="color: var(--accent-primary);">{stats['memory_count']}</div>
          <div class="stat-label">Memories</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: var(--accent-secondary);">{stats['topic_count']}</div>
          <div class="stat-label">Topics</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: var(--highlight);">{stats['confidence_pct']}%</div>
          <div class="stat-label">Confidence</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: var(--accent-secondary);">{stats['connection_count']}</div>
          <div class="stat-label">Connections</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# NeuroLM Production Theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg-base: #0A0A0A;
  --surface-1: #121212;
  --surface-2: #1A1A1A;
  --text-primary: #FFFFFF;
  --text-secondary: #B0B0B0;
  --accent-primary: #7F5AF0;
  --accent-secondary: #2EC4B6;
  --highlight: #FF3366;
  --border-radius: 16px;
}

/* Global Dark Theme */
.stApp {
    background: radial-gradient(circle at 15% 30%, #1A1A1A 0%, transparent 25%),
                radial-gradient(circle at 85% 70%, #0F0F0F 0%, transparent 25%),
                var(--bg-base);
    color: var(--text-primary);
    line-height: 1.7;
}

.main > div {
    background-color: transparent;
}

/* Typography */
h1, h2, h3, h4 {
    color: var(--text-primary) !important;
    font-weight: 700;
    margin-bottom: 1.25rem;
    font-family: 'Inter', sans-serif !important;
}

h1 {
    font-size: 2.8rem;
    letter-spacing: -0.5px;
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin-top: 0;
}

h2 {
    font-size: 2rem;
    border-bottom: 2px solid #333;
    padding-bottom: 0.5rem;
    margin-top: 2.5rem;
}

h3 {
    font-size: 1.6rem;
    color: var(--accent-secondary);
}

p, li, div, span {
    color: var(--text-primary) !important;
    font-size: 1.1rem;
    line-height: 1.8;
    font-family: 'Inter', sans-serif !important;
}

/* Header Styling */
.neuro-header {
    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 50%, var(--highlight) 100%);
    padding: 3rem 2rem;
    border-radius: var(--border-radius);
    margin-bottom: 2rem;
    text-align: center;
    color: white;
    position: relative;
    overflow: hidden;
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
    color: white !important;
}

.neuro-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 1.4rem;
    font-weight: 300;
    margin: 0.5rem 0 0 0;
    opacity: 0.95;
    position: relative;
    z-index: 1;
    color: white !important;
}

/* Input Styling */
.stTextInput > div > div > input {
    background-color: var(--surface-2) !important;
    color: var(--text-primary) !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.75rem 1rem !important;
    font-size: 1.1rem !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 3px rgba(127, 90, 240, 0.1) !important;
}

/* Button Styling */
.stButton > button {
    background: linear-gradient(135deg, var(--accent-primary), #5E35B1) !important;
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    padding: 0.75rem 2rem !important;
    transition: all 0.3s ease !important;
    font-size: 1.1rem !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(127, 90, 240, 0.4) !important;
}

/* Chat Message Styling */
.neural-message {
    background: var(--surface-1);
    border: 1px solid #252525;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    position: relative;
}

/* Sidebar Navigation */
.nav-item {
    display: flex;
    align-items: center;
    padding: 0.8rem 1rem;
    background: transparent;
    border-radius: 12px;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.3s ease;
    color: var(--text-primary) !important;
}

.nav-item:hover {
    background: var(--surface-2);
}

.nav-item.active {
    background: var(--surface-2);
    border-left: 3px solid var(--accent-primary);
}

/* Neural Activity Widget */
.neural-stats {
    background: var(--surface-1);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-bottom: 2rem;
    border: 1px solid #252525;
}

.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1rem;
}

.stat-card {
    background: var(--surface-2);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    border: 1px solid #333;
}

.stat-value {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.stat-label {
    color: var(--text-secondary);
    font-size: 0.9rem;
}

/* Selectbox Styling */
.stSelectbox > div > div {
    background-color: var(--surface-2) !important;
    color: var(--text-primary) !important;
    border: 1px solid #333 !important;
}

/* Sidebar Sections */
.sidebar-section {
    background-color: var(--surface-1);
    padding: 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border: 1px solid #252525;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}

.sidebar-title {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 1rem;
    font-size: 1.1rem;
}

.chat-item {
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    color: var(--text-primary);
    padding: 0.75rem;
    background-color: var(--surface-2);
    border-radius: 8px;
    margin-bottom: 0.75rem;
    cursor: pointer;
    border: 1px solid #333;
    transition: all 0.3s ease;
}

.chat-item:hover {
    background-color: #333;
    border-color: var(--accent-primary);
}

.topic-item {
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin: 0.5rem 0;
    padding: 0.5rem;
    background-color: var(--surface-2);
    border-radius: 6px;
    border-left: 3px solid var(--accent-primary);
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
        
        # Login/Register tabs
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        with tab1:
            st.markdown("### Access Your Neural Network")
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Connect to NeuroLM", use_container_width=True, key="login_btn"):
                if login_username and login_password:
                    success, result = authenticate_user(login_username, login_password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_id = result["user_id"]
                        st.session_state.username = result["username"]
                        st.success("Neural connection established!")
                        st.rerun()
                    else:
                        st.error(result)
                else:
                    st.error("Please enter username and password")
        
        with tab2:
            st.markdown("### Create Neural Account")
            reg_email = st.text_input("Email Address", key="reg_email", placeholder="your@email.com")
            reg_username = st.text_input("Choose Username", key="reg_user", placeholder="username")
            reg_password = st.text_input("Choose Password", type="password", key="reg_pass", placeholder="minimum 6 characters")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="confirm password")
            
            if st.button("Create Account", use_container_width=True, key="register_btn"):
                if reg_email and reg_username and reg_password and reg_confirm:
                    # Validate email format
                    import re
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, reg_email):
                        st.error("Please enter a valid email address")
                    elif reg_password == reg_confirm:
                        if len(reg_password) >= 6:
                            success, message = create_user_account(reg_username, reg_email, reg_password)
                            if success:
                                st.success(message)
                                st.info("You can now login with your new account")
                            else:
                                st.error(message)
                        else:
                            st.error("Password must be at least 6 characters")
                    else:
                        st.error("Passwords don't match")
                else:
                    st.error("Please fill in all fields")
        
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    
    return True

def get_conversation_sessions(user_id, limit=10):
    """Get distinct conversation sessions with their latest messages"""
    if not memory or not user_id:
        return []
    
    try:
        # Get recent conversations and group them into sessions
        all_messages = memory.get_conversation_history(user_id, limit=100)
        if not all_messages:
            return []
        
        # Group messages into conversation sessions
        sessions = []
        current_session = []
        
        for msg in all_messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                role = msg.get("role", "user")
            else:
                content = str(msg)
                role = "unknown"
            
            # Strict filtering for valid content
            if (content and 
                content.strip() and 
                len(content.strip()) > 3 and
                not any(keyword in content.lower() for keyword in ["match", "return", "session.run", "cypher", "neo4j", "driver"])):
                
                current_session.append({"content": content.strip(), "role": role})
                
                # Start new session every 15 messages to create logical breaks
                if len(current_session) >= 15:
                    if current_session:
                        sessions.append(current_session)
                    current_session = []
        
        # Only add session if it has meaningful content
        if current_session and len(current_session) > 0:
            sessions.append(current_session)
        
        # Filter out sessions with no user messages
        valid_sessions = []
        for session in sessions:
            has_user_message = any(msg["role"] == "user" for msg in session)
            if has_user_message and len(session) > 0:
                valid_sessions.append(session)
        
        return valid_sessions[:limit]
    except Exception:
        return []

def load_conversation_session(session_messages):
    """Load a conversation session into the chat interface"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Clear current messages and load the session (last 25 messages)
    from datetime import datetime
    st.session_state.messages = []
    
    for msg in session_messages[-25:]:
        st.session_state.messages.append({
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": datetime.now()
        })
    
    st.rerun()

def start_new_chat():
    """Start a new chat session"""
    if "messages" in st.session_state:
        st.session_state.messages = []
    st.rerun()

def chat_history_sidebar():
    """Display recent conversation sessions in sidebar"""
    # New Chat button at the top
    if st.button("✨ New Chat", key="new_chat_btn", use_container_width=True, help="Start a fresh conversation"):
        start_new_chat()
    
    # Recent Conversations section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">Recent Conversations</div>', unsafe_allow_html=True)
    
    if memory:
        try:
            # Get conversation sessions
            current_user = get_current_user()
            sessions = get_conversation_sessions(current_user, limit=10)
            
            if sessions:
                conversation_count = 0
                for i, session in enumerate(sessions):
                    if session and len(session) > 0:
                        # Get the first user message as preview
                        preview_msg = None
                        for msg in session:
                            if msg["role"] == "user" and msg["content"].strip():
                                preview_msg = msg
                                break
                        
                        if not preview_msg:
                            for msg in session:
                                if msg["content"].strip():
                                    preview_msg = msg
                                    break
                        
                        if preview_msg and preview_msg["content"].strip():
                            content = preview_msg["content"].strip()
                            preview = content[:45] + "..." if len(content) > 45 else content
                            preview = preview.replace('\n', ' ').strip()
                            
                            if preview:  # Only show if there's actual content
                                # Create clickable conversation button
                                if st.button(f"💬 {preview}", key=f"conv_{i}", use_container_width=True, help=f"Load conversation ({len(session)} messages)"):
                                    load_conversation_session(session)
                                conversation_count += 1
                
                if conversation_count == 0:
                    st.markdown('<div class="topic-item">No conversations yet</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="topic-item">No conversations yet</div>', unsafe_allow_html=True)
            
        except Exception:
            st.markdown('<div class="topic-item">Connecting to neural network...</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="topic-item">Neural memory system offline</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)



# Move main() to end of file - will be added after all function definitions

def analytics_sidebar():
    """Analytics page sidebar content"""
    if memory:
        try:
            stats = memory.get_memory_stats(get_current_user())
            
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-title">Memory Insights</div>', unsafe_allow_html=True)
            
            if stats.get("top_topics"):
                for topic, count in stats["top_topics"][:3]:
                    if isinstance(topic, str) and len(topic.strip()) > 0:
                        st.markdown(f'<div class="topic-item">{topic}: {count} mentions</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception:
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-title">Analytics</div>', unsafe_allow_html=True)
            st.markdown('<div class="topic-item">Loading data...</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

def explorer_sidebar():
    """Explorer page sidebar content"""
    if memory:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-title">Memory Search</div>', unsafe_allow_html=True)
        
        search_query = st.text_input("Search memories", key="memory_search", label_visibility="collapsed")
        
        if search_query:
            try:
                results = memory.get_relevant_memories(search_query, get_current_user(), limit=5)
                if results:
                    for result in results:
                        preview = result[:40] + "..." if len(result) > 40 else result
                        st.markdown(f'<div class="chat-item">{preview}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="topic-item">No matches found</div>', unsafe_allow_html=True)
            except Exception:
                st.markdown('<div class="topic-item">Search unavailable</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def analytics_dashboard():
    """Analytics dashboard with real data"""
    neural_activity_widget(get_current_user())
    
    if memory:
        try:
            stats = memory.get_memory_stats(get_current_user())
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Top Discussion Topics")
                if stats.get("top_topics"):
                    for topic, count in stats["top_topics"][:5]:
                        if isinstance(topic, str) and len(topic.strip()) > 0:
                            st.markdown(f"**{topic}**: {count} mentions")
                else:
                    st.info("No topics analyzed yet")
            
            with col2:
                st.markdown("### Memory Statistics")
                st.metric("Total Memories", stats.get("total_memories", 0))
                st.metric("Strong Memories", stats.get("strong_memories", 0))
                st.metric("Average Confidence", f"{stats.get('avg_confidence', 0)*100:.1f}%")
                
        except Exception as e:
            st.error("Analytics data temporarily unavailable")

def memory_explorer():
    """Memory explorer interface"""
    st.markdown("### Memory Network Explorer")
    
    if memory:
        try:
            # Get all memories for exploration
            memory_count = memory.get_memory_count(get_current_user())
            st.info(f"Exploring {memory_count} stored memories")
            
            # Simple memory browser
            if memory_count > 0:
                recent_memories = memory.get_conversation_history(get_current_user(), limit=10)
                
                if recent_memories:
                    st.markdown("### Recent Memories")
                    for i, mem in enumerate(recent_memories):
                        if isinstance(mem, dict):
                            content = mem.get("content", "")
                            role = mem.get("role", "unknown")
                        else:
                            content = str(mem)
                            role = "memory"
                        
                        if content and len(content.strip()) > 0:
                            # Filter out code/query content
                            if not any(keyword in content.lower() for keyword in ["match", "return", "session.run"]):
                                with st.expander(f"Memory {i+1} ({role})"):
                                    st.write(content[:500] + "..." if len(content) > 500 else content)
            else:
                st.info("No memories to explore yet. Start a conversation to build your neural network.")
                
        except Exception as e:
            st.error("Memory explorer temporarily unavailable")
    else:
        st.error("Memory system not available")

def chat_interface():
    """Main chat interface with neural messages"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display existing messages using neural components
    for message in st.session_state.messages:
        neural_message(
            content=message["content"],
            sender="AI" if message["role"] == "assistant" else "user",
            timestamp=message.get("timestamp")
        )
    
    if prompt := st.chat_input("What would you like to discuss?"):
        from datetime import datetime
        
        # Add user message to session
        user_message = {"role": "user", "content": prompt, "timestamp": datetime.now()}
        st.session_state.messages.append(user_message)
        
        # Display user message
        neural_message(content=prompt, sender="user", timestamp=datetime.now())
        
        # Store user message in memory
        if memory:
            try:
                memory.store_chat(get_current_user(), "user", prompt)
            except Exception as e:
                st.warning(f"Memory storage issue: {str(e)}")
        
        # Get relevant memories for context
        context = []
        if memory:
            with st.spinner("Accessing neural network..."):
                try:
                    context = memory.get_relevant_memories(prompt, get_current_user())
                except Exception as e:
                    st.warning(f"Memory retrieval issue: {str(e)}")
        
        # Generate AI response
        try:
            context_str = "\n\n".join([f"- {mem}" for mem in context]) if context else ""
            enhancements = " with access to your personal neural network" if context else ""
            context_section = f'Relevant Neural Context:\n{context_str}' if context_str else ''
            
            system_prompt = f"""You are NeuroLM, an advanced neural language model{enhancements}.

Your capabilities:
1. Recall and reference past conversations naturally
2. Connect information across different discussions
3. Provide thoughtful, contextual responses
4. Build on previous discussions to create continuity

{context_section}

You are an intelligent AI assistant designed to act as the user's neural memory system."""
            
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
            
            # Stream response and display with neural component
            full_response = ""
            response_placeholder = st.empty()
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    # Update placeholder with streaming text
                    with response_placeholder.container():
                        neural_message(
                            content=full_response + "▌",
                            sender="AI",
                            timestamp=datetime.now(),
                            sources=context[:3] if context else None
                        )
            
            # Final response display
            with response_placeholder.container():
                neural_message(
                    content=full_response,
                    sender="AI",
                    timestamp=datetime.now(),
                    sources=context[:3] if context else None
                )
            
            # Add to session and store in memory
            assistant_message = {"role": "assistant", "content": full_response, "timestamp": datetime.now()}
            st.session_state.messages.append(assistant_message)
            
            if memory:
                try:
                    memory.store_chat(get_current_user(), "assistant", full_response)
                except Exception as e:
                    st.warning(f"Failed to store AI response: {str(e)}")
                    
        except Exception as e:
            error_response = "I apologize, but I'm experiencing technical difficulties. Please check your OpenRouter API key configuration."
            neural_message(content=error_response, sender="AI", timestamp=datetime.now())
            st.session_state.messages.append({"role": "assistant", "content": error_response, "timestamp": datetime.now()})

def main():
    if check_login():
        # Navigation state
        if "page" not in st.session_state:
            st.session_state.page = "chat"
        
        # Header
        st.markdown("""
        <div class="neuro-header">
            <h1 class="neuro-title">NeuroLM</h1>
            <p class="neuro-subtitle">Your Personal Neural Language Model</p>
        </div>
        """, unsafe_allow_html=True)
        

        
        # Sidebar with navigation
        with st.sidebar:
            # Neural branding
            st.markdown("""
            <div style="padding: 1.5rem 0; border-bottom: 1px solid #252525; margin-bottom: 1.5rem;">
              <div style="display: flex; align-items: center;">
                <div style="font-size: 1.8rem; margin-right: 12px;">🧠</div>
                <div>
                  <div style="font-size: 1.4rem; font-weight: 700; color: var(--text-primary);">NeuroLM</div>
                  <div style="color: var(--text-secondary); font-size: 0.9rem;">Neural Memory System</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add some spacing before sidebar content
            st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
            
            # Sidebar content for chat
            chat_history_sidebar()
            
            # Push content to bottom
            st.markdown("<div style='flex: 1;'></div>", unsafe_allow_html=True)
            
            # Compact user profile at bottom
            current_username = st.session_state.get("username", "User")
            user_initial = current_username[0].upper() if current_username else "U"
            
            st.markdown(f"""
            <div style="padding: 0.75rem; background: rgba(18, 18, 18, 0.6); border-top: 1px solid #333; margin: 0 -1rem -1rem -1rem;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 24px; height: 24px; border-radius: 4px; background: rgba(127, 90, 240, 0.3); display: flex; align-items: center; justify-content: center;">
                  <span style="color: var(--accent-primary); font-weight: 600; font-size: 10px;">{user_initial}</span>
                </div>
                <div style="flex: 1;">
                  <div style="font-size: 0.8rem; color: var(--text-primary); opacity: 0.9;">{current_username}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Small logout button
            if st.button("Logout", key="logout_btn", help="Disconnect from NeuroLM"):
                st.session_state.authenticated = False
                st.rerun()
        
        # Main chat interface
        chat_interface()

if __name__ == "__main__":
    main()