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
        st.sidebar.warning(f"Neo4j connection issue: {str(e)}")
        return None

memory = init_memory()
DEFAULT_USER = "default_user"

# This line was moved to fix the Streamlit configuration error

# Custom CSS for sleek interface
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%);
        color: white;
    }
    .stSidebar {
        background: linear-gradient(180deg, #111827 0%, #1f2937 100%);
    }
</style>
""", unsafe_allow_html=True)

# Simple login check
def check_login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        with st.sidebar:
            st.markdown("### 🔐 Second Brain Access")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("🧠 Access Brain"):
                app_user = os.getenv("APP_USERNAME")
                app_pass = os.getenv("APP_PASSWORD")
                
                if not app_user or not app_pass:
                    st.error("App credentials not configured")
                    return False
                
                if username == app_user and password == app_pass:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        return False
    return True

# Main interface
def main():
    if check_login():
        st.title("🧠 Second Brain AI")
        st.write("Welcome to your AI assistant!")
        
        with st.sidebar:
            st.markdown("### 🎛️ Brain Controls")
            st.markdown("---")
            
            if st.button("🚪 Logout"):
                st.session_state.authenticated = False
                st.rerun()
            
            # Enhanced Associative Memory Stats
            if memory:
                try:
                    stats = memory.get_memory_stats(DEFAULT_USER)
                    
                    # Core memory metrics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("🧠 Total Memories", stats["total_memories"])
                        st.metric("💪 Strong Memories", stats["strong_memories"])
                    with col2:
                        st.metric("📊 Avg Confidence", f"{stats['avg_confidence']*100:.1f}%")
                        st.metric("🔄 Total Accesses", stats["total_accesses"])
                    
                    # Associative connection metrics  
                    st.markdown("**🔗 Neural Connections**")
                    col3, col4 = st.columns(2)
                    with col3:
                        st.metric("🕸️ Total Links", stats["total_connections"])
                        st.metric("⚡ Strong Links", stats["strong_connections"])
                    with col4:
                        connection_pct = f"{stats['avg_connection_strength']*100:.1f}%"
                        st.metric("🎯 Link Strength", connection_pct)
                        
                        # Brain connectivity indicator
                        if stats["total_connections"] > 10:
                            st.success("🧠 Highly Connected Brain")
                        elif stats["total_connections"] > 5:
                            st.info("🌱 Growing Neural Network")
                        else:
                            st.info("🌟 Building Connections")
                    
                    st.success("✅ Enhanced Associative Brain Active")
                    
                    # Memory reinforcement button
                    if st.button("🧠 Strengthen Memories"):
                        with st.spinner("Consolidating neural pathways..."):
                            memory.reinforce_memories(DEFAULT_USER)
                        st.success("Memory reinforcement complete!")
                        st.rerun()
                        
                except Exception as e:
                    st.warning(f"Memory system issue: {str(e)}")
            else:
                st.info("💡 Using session memory only")
            
            st.markdown("---")
        
        # Simple chat interface
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        if prompt := st.chat_input("Share your thoughts with your Second Brain..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Store user message in Neo4j
            if memory:
                try:
                    memory.store_chat(DEFAULT_USER, "user", prompt)
                except Exception as e:
                    st.warning(f"Failed to store message: {str(e)}")
            
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get relevant memories for context
            context = []
            if memory:
                with st.spinner("🧠 Accessing memories..."):
                    try:
                        context = memory.get_relevant_memories(prompt, DEFAULT_USER)
                        if context:
                            st.success(f"🎯 Found {len(context)} relevant memories!")
                    except Exception as e:
                        st.warning(f"Memory retrieval issue: {str(e)}")
            
            # Get AI response with streaming
            with st.chat_message("assistant"):
                try:
                    # Build context string
                    context_str = "\n\n".join([f"- {mem}" for mem in context]) if context else ""
                    enhancements = " (Enhanced by your personal knowledge)" if context else ""
                    
                    context_section = f'Relevant Context from Knowledge Base:\n{context_str}' if context_str else ''
                    
                    system_prompt = f"""You are a sophisticated second brain assistant{enhancements} with access to the user's conversation history and knowledge.
                    
Your role is to:
1. Recall and reference past conversations naturally
2. Incorporate relevant knowledge from your memory
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