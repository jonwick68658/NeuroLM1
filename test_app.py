import streamlit as st
import openai
import os
from dotenv import load_dotenv
from memory import Neo4jMemory
from utils import split_text
import PyPDF2
import docx2txt

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
openai_client = openai.OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Initialize memory system with graceful fallback
@st.cache_resource
def init_memory():
    try:
        return Neo4jMemory()
    except Exception as e:
        st.sidebar.warning(f"Neo4j connection issue: {str(e)}")
        return None

memory = init_memory()
DEFAULT_USER = "default_user"

# Configure page
st.set_page_config(
    page_title="Second-Brain-AI",
    page_icon="🧠",
    layout="wide"
)

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
            if st.button("🚪 Logout"):
                st.session_state.authenticated = False
                st.rerun()
            
            st.markdown("---")
            
            # Memory stats
            if memory:
                try:
                    memory_count = memory.get_memory_count(DEFAULT_USER)
                    st.metric("🧠 Total Memories", memory_count)
                    st.success("✅ Neo4j Memory Connected")
                except Exception as e:
                    st.warning(f"Memory retrieval issue: {str(e)}")
            else:
                st.info("💡 Using session memory (Neo4j offline)")
            
            st.markdown("---")
            
            # Document uploader
            st.markdown("### 📚 Knowledge Upload")
            uploaded = st.file_uploader(
                "Upload documents", 
                type=["pdf", "txt", "docx"],
                help="Add documents to enhance your AI's knowledge"
            )
            
            if uploaded and memory:
                with st.spinner("Processing document..."):
                    try:
                        content = ""
                        if uploaded.type == "application/pdf":
                            reader = PyPDF2.PdfReader(uploaded)
                            content = "\n".join([page.extract_text() for page in reader.pages])
                        elif uploaded.type == "text/plain":
                            content = uploaded.getvalue().decode()
                        elif uploaded.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                            content = docx2txt.process(uploaded)
                        
                        if content.strip():
                            chunks = split_text(content)
                            for chunk in chunks:
                                memory.store_knowledge(DEFAULT_USER, chunk, uploaded.name)
                            st.success(f"📚 Added {len(chunks)} knowledge chunks!")
                        else:
                            st.warning("No text content found")
                    except Exception as e:
                        st.error(f"Document processing error: {str(e)}")
        
        # Simple chat interface
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        if prompt := st.chat_input("Share your thoughts with your Second Brain..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Store in Neo4j if available
            if memory:
                try:
                    memory.store_chat(DEFAULT_USER, "user", prompt)
                except Exception as e:
                    st.sidebar.warning(f"Memory storage issue: {str(e)}")
            
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get relevant memories if Neo4j is connected
            context = []
            if memory:
                try:
                    context = memory.get_relevant_memories(prompt, DEFAULT_USER)
                    if context:
                        st.sidebar.success(f"🎯 Found {len(context)} relevant memories!")
                except Exception as e:
                    st.sidebar.warning(f"Memory retrieval issue: {str(e)}")
            
            # Get AI response with streaming
            with st.chat_message("assistant"):
                try:
                    # Build enhanced prompt with context
                    context_str = "\n\n".join([f"- {mem}" for mem in context]) if context else ""
                    enhancements = " (Enhanced with your personal knowledge)" if context else ""
                    
                    context_section = f'Relevant Context from Knowledge Base:\n{context_str}' if context_str else ''
                    
                    system_prompt = f"""You are a sophisticated second brain assistant{enhancements}. Help the user with thoughtful, contextual responses. 
                    
Your role is to:
1. Provide helpful and insightful responses
2. Remember context from this conversation and stored memories
3. Be engaging and supportive
4. Think step by step when solving problems

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
                    
                    # Store AI response in Neo4j if available
                    if memory:
                        try:
                            memory.store_chat(DEFAULT_USER, "assistant", full_response)
                        except Exception as e:
                            st.sidebar.warning(f"Memory storage issue: {str(e)}")
                        
                except Exception as e:
                    st.error(f"AI Response Error: {str(e)}")
                    error_response = "I apologize, but I'm experiencing technical difficulties. Please check your OpenRouter API key and try again."
                    st.markdown(error_response)
                    st.session_state.messages.append({"role": "assistant", "content": error_response})

if __name__ == "__main__":
    main()