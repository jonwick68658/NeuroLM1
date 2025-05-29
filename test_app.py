import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
        
        # Simple chat interface
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        if prompt := st.chat_input("Say hello to test the interface"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            response = f"Echo: {prompt} (This is a test response - full AI integration pending)"
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.write(response)

if __name__ == "__main__":
    main()