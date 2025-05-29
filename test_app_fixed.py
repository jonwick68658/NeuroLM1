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

# Custom CSS for sleek interface
st.markdown("""
<style>
.stTextInput > div > div > input {
    background-color: #2b2b2b;
    color: white;
    border-radius: 10px;
}
.stButton > button {
    background-color: #4CAF50;
    color: white;
    border-radius: 10px;
    border: none;
    padding: 0.5rem 1rem;
    transition: background-color 0.3s;
}
.stButton > button:hover {
    background-color: #45a049;
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
            
            # Advanced Memory Stats
            if memory:
                try:
                    stats = memory.get_memory_stats(DEFAULT_USER)
                    st.metric("🧠 Total Memories", stats["total_memories"])
                    st.metric("💪 Strong Memories", stats["strong_memories"])
                    st.metric("📊 Avg Confidence", f"{stats['avg_confidence']*100:.1f}%")
                    st.metric("🔄 Total Accesses", stats["total_accesses"])
                    st.success("✅ Biomemetic Brain Active")
                    
                    # Memory reinforcement button
                    if st.button("🧠 Strengthen Memories"):
                        with st.spinner("Consolidating memories..."):
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