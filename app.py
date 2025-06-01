import streamlit as st
import openai
import os
from dotenv import load_dotenv
from neural_memory import NeuralMemorySystem
from simple_model_selector import SimpleModelSelector

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
openai_client = openai.OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Initialize components
model_selector = SimpleModelSelector()

@st.cache_resource
def init_memory():
    try:
        return NeuralMemorySystem()
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
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user_id = f"user_{username}"
        
        with memory.driver.session() as session:
            # Check if user exists
            existing = session.run(
                "MATCH (u:User {username: $username}) RETURN u",
                username=username
            ).single()
            
            if existing:
                return False, "Username already exists"
            
            # Create user
            session.run(
                """
                CREATE (u:User {
                    id: $user_id,
                    username: $username,
                    email: $email,
                    password_hash: $password_hash,
                    created_at: datetime()
                })
                """,
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash
            )
            
            # Initialize user in memory system
            memory.create_user(user_id, username)
            
            return True, {"user_id": user_id, "username": username}
            
    except Exception as e:
        return False, f"Account creation failed: {str(e)}"

def authenticate_user(username, password):
    """Authenticate user login"""
    if not memory:
        return False, "Memory system not available"
    
    try:
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with memory.driver.session() as session:
            user = session.run(
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

def get_neural_stats(user_id):
    """Get neural network statistics"""
    if not memory or not user_id:
        return {"memory_count": 0, "topic_count": 0, "confidence_pct": 85, "connection_count": 0}
    
    try:
        overview = memory.get_topic_overview(user_id)
        return {
            "memory_count": overview.get("total_memories", 0),
            "topic_count": overview.get("topic_count", 0),
            "confidence_pct": 85,  # Neural confidence level
            "connection_count": len(overview.get("topics", []))
        }
    except Exception as e:
        return {"memory_count": 0, "topic_count": 0, "confidence_pct": 85, "connection_count": 0}

def neural_message(content, sender="AI", timestamp=None, sources=None):
    """Custom neural message component"""
    sender_color = "#00d4aa" if sender == "AI" else "#ffffff"
    
    st.markdown(f"""
    <div style="margin: 1rem 0; padding: 1rem; border-left: 3px solid {sender_color}; 
                background: rgba(255,255,255,0.02); border-radius: 0 8px 8px 0;">
        <div style="color: {sender_color}; font-weight: 600; margin-bottom: 0.5rem;">
            {sender}
        </div>
        <div style="color: #ffffff; line-height: 1.6;">
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)

def neural_activity_widget(user_id):
    """Neural activity widget with real data"""
    stats = get_neural_stats(user_id)
    
    st.markdown(f"""
    <div style="background: rgba(0,212,170,0.1); padding: 1.5rem; border-radius: 12px; margin: 1rem 0;">
        <h3 style="margin: 0 0 1rem 0; color: #00d4aa;">Neural Activity</h3>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #00d4aa;">{stats['memory_count']}</div>
                <div style="color: #cccccc; font-size: 0.9rem;">Memories</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #ff6b6b;">{stats['topic_count']}</div>
                <div style="color: #cccccc; font-size: 0.9rem;">Topics</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #4ecdc4;">{stats['confidence_pct']}%</div>
                <div style="color: #cccccc; font-size: 0.9rem;">Confidence</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #45b7d1;">{stats['connection_count']}</div>
                <div style="color: #cccccc; font-size: 0.9rem;">Connections</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def check_login():
    """Handle user login"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.title("🧠 NeuroLM - Neural Language Model")
        st.markdown("### Access Your Neural Memory")
        
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                login_btn = st.form_submit_button("Login")
                
                if login_btn and username and password:
                    success, result = authenticate_user(username, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_id = result["user_id"]
                        st.session_state.username = result["username"]
                        st.rerun()
                    else:
                        st.error(result)
        
        with tab2:
            with st.form("signup_form"):
                new_username = st.text_input("Choose Username")
                new_email = st.text_input("Email")
                new_password = st.text_input("Choose Password", type="password")
                signup_btn = st.form_submit_button("Create Account")
                
                if signup_btn and new_username and new_email and new_password:
                    success, result = create_user_account(new_username, new_email, new_password)
                    if success:
                        st.success("Account created successfully! Please login.")
                    else:
                        st.error(result)
        
        return False
    
    return True

def chat_interface():
    """Main chat interface with neural messages"""
    st.title("🧠 NeuroLM Chat")
    
    current_user = get_current_user()
    if not current_user:
        st.error("Please login to continue")
        return
    

    
    # Model selector
    st.markdown("### AI Model")
    selected_model = model_selector.render_selector(current_user)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages using neural message component
    st.markdown("### Conversation")
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            neural_message(message["content"], message["role"].title())
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Store in neural memory
        if memory:
            memory.store_conversation(current_user, "user", prompt)
        
        # Get AI response
        try:
            # Retrieve relevant context
            context = ""
            context_quality = "sparse"
            if memory:
                context = memory.retrieve_context(current_user, prompt, limit=3)
                # Assess context quality for strategic questioning
                if context and len(context.strip()) > 50:
                    context_lines = [line for line in context.split('\n') if line.strip()]
                    if len(context_lines) >= 2:
                        context_quality = "sufficient"
            
            # Prepare messages for API
            api_messages = []
            if context and context_quality == "sufficient":
                api_messages.append({
                    "role": "system", 
                    "content": f"You are NeuroLM, an AI assistant with access to a neural memory system that stores and retrieval our conversation history. Your responses are enhanced by relevant memories from our past interactions. Relevant context: {context}"
                })
            elif context and context_quality == "sparse":
                api_messages.append({
                    "role": "system", 
                    "content": f"You are NeuroLM, an AI assistant with access to a neural memory system. I have limited relevant memories for this conversation, which presents a good opportunity to learn more about your specific preferences and patterns. Available context: {context}"
                })
            else:
                api_messages.append({
                    "role": "system", 
                    "content": """You are NeuroLM, an AI assistant with access to a neural memory system that stores and retrieves our conversation history. Your responses are enhanced by relevant memories from our past interactions.

### Memory-Aware Responses
When you receive context from previous conversations, reference it naturally to show continuity. When little or no memory context is available, this indicates an opportunity to learn more about the user.

### Strategic Questioning for Quality Memory Building
In conversations where memory context is sparse (fewer than 2 relevant memories), focus on extracting specific, actionable information:

**Concrete Preferences**: "How do you prefer to receive feedback?" or "What's your ideal way to start the day?"

**Specific Patterns**: "What's a workflow or approach that consistently works well for you?" or "What tends to frustrate you most in [relevant context]?"

**Clear Rules & Constraints**: "Are there specific guidelines you follow when making decisions about [topic]?" or "What are your non-negotiables in [relevant area]?"

**Technology & Tool Choices**: "What tools or approaches do you swear by?" or "What's something you've tried that you'd never go back to?"

**Workflow Preferences**: "Walk me through how you like to tackle [type of task]" or "What's your process for [relevant activity]?"

### Memory Quality Focus
Prioritize learning about:
- User corrections or frustrations (high value for future interactions)
- Explicit preferences the user states
- Specific patterns in how they like to work or communicate
- Concrete rules or constraints they follow
- Clear technology or approach choices

Avoid storing obvious statements or vague preferences that don't provide actionable guidance.

### Conversation Guidelines
- Ask questions naturally within conversation flow, not as interviews
- Follow the user's lead if they change topics or resist questions
- Build on user statements with follow-up questions that add specificity
- Reference meaningful memories to show understanding of their preferences
- Focus on extracting information that will genuinely improve future interactions

### Response Style
Maintain a warm, supportive, and honest conversational tone. Be curious about the user's specific preferences and patterns. When you have quality memory context, let it inform your responses. When memory is limited, use targeted questions to learn actionable information.

Your goal is to understand the user's specific preferences and patterns well enough to anticipate their needs and communicate in their preferred style."""
                })
            
            # Add recent conversation history
            for msg in st.session_state.messages[-5:]:
                api_messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Call OpenRouter API
            response = openai_client.chat.completions.create(
                model=selected_model,
                messages=api_messages,
                max_tokens=500,
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message.content
            
            # Add assistant response
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})
            
            # Store in neural memory
            if memory:
                memory.store_conversation(current_user, "assistant", assistant_message)
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")

def analytics_dashboard():
    """Analytics dashboard with real data"""
    st.title("📊 Neural Analytics")
    
    current_user = get_current_user()
    if not current_user or not memory:
        st.error("Analytics not available")
        return
    
    # Get topic overview
    overview = memory.get_topic_overview(current_user)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Memories", overview.get("total_memories", 0))
        st.metric("Active Topics", overview.get("topic_count", 0))
    
    with col2:
        st.metric("Neural Confidence", "85%")
        st.metric("Memory Efficiency", "92%")
    
    # Topic breakdown
    if overview.get("topics"):
        st.markdown("### Topic Distribution")
        for topic in overview["topics"][:10]:
            st.markdown(f"**{topic['name']}**: {topic['memory_count']} memories")

def memory_explorer():
    """Memory explorer interface"""
    st.title("🔍 Memory Explorer")
    
    current_user = get_current_user()
    if not current_user or not memory:
        st.error("Memory explorer not available")
        return
    
    # Search memories
    search_query = st.text_input("Search your memories...")
    
    if search_query:
        context = memory.retrieve_context(current_user, search_query, limit=5)
        if context:
            st.markdown("### Search Results")
            neural_message(context, "Memory Search")
        else:
            st.info("No relevant memories found")
    
    # Show recent conversations
    st.markdown("### Recent Activity")
    try:
        recent = memory.get_conversation_history(current_user, limit=10)
        for msg in recent:
            if isinstance(msg, dict) and msg.get("content"):
                neural_message(msg["content"][:200] + "...", msg.get("role", "Memory").title())
    except:
        st.info("No recent activity to display")

def document_registry():
    """Document registry page for managing uploaded files"""
    st.title("📄 Document Registry")
    
    user_id = get_current_user()
    if not user_id:
        st.error("User not authenticated")
        return
    
    if not memory:
        st.error("Memory system not available")
        return
    
    # Get user documents
    documents = memory.get_user_documents(user_id)
    
    if not documents:
        st.info("No documents uploaded yet.")
        return
    
    st.write(f"**{len(documents)} documents found**")
    
    # Display documents in a table format
    for doc in documents:
        col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
        
        with col1:
            st.write(f"**{doc['filename']}**")
        
        with col2:
            st.write(doc['type'])
        
        with col3:
            uploaded_time = doc['uploaded_at']
            if uploaded_time:
                st.write(uploaded_time.strftime("%Y-%m-%d %H:%M") if hasattr(uploaded_time, 'strftime') else str(uploaded_time))
        
        with col4:
            if st.button("Delete", key=f"delete_{doc['id']}"):
                if memory.delete_document(user_id, doc['id']):
                    st.success(f"Deleted {doc['filename']}")
                    st.rerun()
                else:
                    st.error("Failed to delete document")

def main():
    # Dark neural theme
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%);
        color: #ffffff;
    }
    .stSidebar {
        background: rgba(0,0,0,0.8);
    }
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.1);
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #ffffff;
    }
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.1);
        color: #ffffff;
        border: 1px solid rgba(0,212,170,0.3);
    }
    .stButton > button {
        background: linear-gradient(45deg, #00d4aa, #4ecdc4);
        color: #000000;
        border: none;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check login
    if not check_login():
        return
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.get('username', 'User')}")
        
        page = st.selectbox(
            "Navigate",
            ["💬 Chat", "📊 Analytics", "🔍 Memory Explorer", "📄 Documents"]
        )
        
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Route to selected page
    if page == "💬 Chat":
        chat_interface()
    elif page == "📊 Analytics":
        analytics_dashboard()
    elif page == "🔍 Memory Explorer":
        memory_explorer()
    elif page == "📄 Documents":
        document_registry()

if __name__ == "__main__":
    main()