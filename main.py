import streamlit as st
import openai
import os
from memory import Neo4jMemory
from utils import generate_embedding, split_text
import time
from dotenv import load_dotenv
import PyPDF2
import docx2txt

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Second-Brain-AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for black glossy interface
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%);
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
        max-width: 800px;
    }
    
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    .stChatMessage[data-testid="user-message"] {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .stChatMessage[data-testid="assistant-message"] {
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        border: 1px solid rgba(75, 85, 99, 0.3);
    }
    
    .stChatInputContainer {
        background: rgba(0, 0, 0, 0.8);
        border-radius: 25px;
        border: 2px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    }
    
    .stSidebar {
        background: linear-gradient(180deg, #111827 0%, #1f2937 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stTitle {
        color: #ffffff;
        text-align: center;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
        background: linear-gradient(90deg, #00ff9f, #00b4d8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .stCaption {
        text-align: center;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 2rem;
    }
    
    .success-message {
        background: rgba(0, 255, 159, 0.1);
        border: 1px solid rgba(0, 255, 159, 0.3);
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Link OpenRouter
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = os.getenv("OPENROUTER_API_KEY")

# Initialize memory system
@st.cache_resource
def init_memory():
    return Neo4jMemory()

try:
    memory = init_memory()
    DEFAULT_USER = "default_user"
except Exception as e:
    st.error(f"Failed to initialize Neo4j connection: {str(e)}")
    st.stop()

# Authentication
def check_login():
    """Handle user login"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        with st.sidebar:
            st.markdown("### 🔐 Second Brain Access")
            st.markdown("---")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧠 Access Brain", use_container_width=True):
                    if len(username) == 0 or len(password) == 0:
                        st.error("⚠️ Missing credentials")
                        return False
                    
                    if (username == os.getenv("APP_USERNAME") and 
                        password == os.getenv("APP_PASSWORD")):
                        st.session_state.authenticated = True
                        st.session_state.messages = []
                        st.success("✅ Access granted!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
            
            with col2:
                if st.button("ℹ️ Help", use_container_width=True):
                    st.info("Check your .env file for correct credentials")
        
        return False
    return True

# Document uploader
def document_uploader():
    with st.sidebar:
        st.markdown("### 📚 Knowledge Ingestion")
        st.markdown("---")
        uploaded = st.file_uploader(
            "Feed Knowledge to Brain", 
            type=["pdf", "txt", "docx"],
            help="Upload documents to enhance the AI's knowledge base"
        )
        
        if uploaded is not None:
            with st.spinner("🧠 Processing document..."):
                try:
                    content = ""
                    if uploaded.type == "application/pdf":
                        reader = PyPDF2.PdfReader(uploaded)
                        content = "\n".join([page.extract_text() for page in reader.pages])
                    elif uploaded.type == "text/plain":
                        content = uploaded.getvalue().decode()
                    elif uploaded.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                        content = docx2txt.process(uploaded)
                    
                    # Save to knowledge base
                    if content.strip():
                        chunks = split_text(content)
                        for chunk in chunks:
                            memory.store_knowledge(DEFAULT_USER, chunk, uploaded.name)
                        
                        st.markdown(f"""
                        <div class="success-message">
                            <strong>📚 Knowledge Added!</strong><br>
                            Added {len(chunks)} knowledge chunks from {uploaded.name}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ No text content found in the document")
                        
                except Exception as e:
                    st.error(f"❌ Error processing document: {str(e)}")

# Main chat interface
def chat_interface():
    st.markdown('<h1 class="stTitle">🧠 Second Brain AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="stCaption">Powered by Neo4j Memory Core & OpenRouter GPT-4o-mini</p>', unsafe_allow_html=True)
    
    # Sidebar features
    with st.sidebar:
        st.markdown("### 🎛️ Brain Controls")
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.messages = []
            st.rerun()
        
        # Memory stats
        try:
            memory_count = memory.get_memory_count(DEFAULT_USER)
            st.metric("🧠 Total Memories", memory_count)
        except Exception as e:
            st.warning(f"Could not fetch memory stats: {str(e)}")
        
        st.markdown("---")
    
    # Document uploader
    document_uploader()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle user input
    if prompt := st.chat_input("Share your thoughts with your Second Brain...", key="chat_input"):
        # Store and display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        try:
            memory.store_chat(DEFAULT_USER, "user", prompt)
        except Exception as e:
            st.error(f"Failed to store message: {str(e)}")
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get relevant memories
        with st.spinner("🧠 Accessing knowledge base..."):
            try:
                context = memory.get_relevant_memories(prompt, DEFAULT_USER)
                if context:
                    st.success(f"🎯 Found {len(context)} relevant memories!")
                else:
                    st.info("💭 Building new memories...")
            except Exception as e:
                st.warning(f"Memory retrieval issue: {str(e)}")
                context = []
        
        # Build LLM prompt with context
        context_str = "\n\n".join([f"- {mem}" for mem in context]) if context else ""
        enhancements = " (Enhanced by your personal knowledge)" if context else ""
        
        system_prompt = f"""You are a sophisticated second brain assistant{enhancements} with access to the user's conversation history and uploaded knowledge.
        
Your role is to:
1. Recall and reference past conversations naturally
2. Incorporate relevant knowledge from uploaded documents
3. Provide thoughtful, contextual responses
4. Build on previous discussions to create continuity

{f'Relevant Context from Knowledge Base:\\n{context_str}' if context_str else ''}

Current conversation context: {len(st.session_state.messages)} messages in this session.
"""
        
        # Get AI response with streaming
        with st.chat_message("assistant"):
            try:
                response = openai.chat.completions.create(
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
                
                # Save AI response
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                try:
                    memory.store_chat(DEFAULT_USER, "assistant", full_response)
                except Exception as e:
                    st.warning(f"Failed to store AI response: {str(e)}")
                    
            except Exception as e:
                st.error(f"❌ AI Response Error: {str(e)}")
                error_response = "I apologize, but I'm experiencing technical difficulties. Please check your OpenRouter API key and try again."
                st.markdown(error_response)
                st.session_state.messages.append({"role": "assistant", "content": error_response})

# Main application flow
def main():
    # Check environment variables
    required_vars = ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "OPENROUTER_API_KEY", "APP_USERNAME", "APP_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        st.info("Please check your .env file and ensure all required variables are set.")
        st.stop()
    
    # Authentication and main interface
    if check_login():
        chat_interface()

if __name__ == "__main__":
    main()
