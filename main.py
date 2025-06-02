from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from memory_api import *
from pydantic import BaseModel
import uvicorn
import os
import httpx
import hashlib
import uuid
from typing import Optional

# Create FastAPI application
app = FastAPI(title="NeuroLM Memory System", version="1.0.0")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-here")

# Include memory API routes
app.include_router(router, prefix="/api")

# Global session storage (in production, use Redis or database)
user_sessions = {}
memory_system = MemorySystem()

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user_in_db(username: str, email: str, password_hash: str) -> bool:
    """Create user in Neo4j database"""
    try:
        with memory_system.driver.session() as session:
            # Check if username already exists
            result = session.run(
                "MATCH (u:User {username: $username}) RETURN u",
                username=username
            )
            if result.single():
                return False  # Username already exists
            
            # Create new user
            session.run(
                "CREATE (u:User {id: $id, username: $username, email: $email, password_hash: $password_hash, created_at: datetime()})",
                id=str(uuid.uuid4()),
                username=username,
                email=email,
                password_hash=password_hash
            )
            return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def verify_user_login(username: str, password: str) -> Optional[str]:
    """Verify user login and return user ID if successful"""
    try:
        with memory_system.driver.session() as session:
            password_hash = hash_password(password)
            result = session.run(
                "MATCH (u:User {username: $username, password_hash: $password_hash}) RETURN u.id as user_id",
                username=username,
                password_hash=password_hash
            )
            record = result.single()
            return record["user_id"] if record else None
    except Exception as e:
        print(f"Error verifying login: {e}")
        return None

# Registration and login pages
@app.get("/register")
async def register_page():
    """Serve registration page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NeuroLM - Register</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
            }
            .register-container {
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
            }
            .logo {
                text-align: center;
                margin-bottom: 2rem;
            }
            .logo h1 {
                color: #4a6fa5;
                margin: 0;
                font-size: 2rem;
                font-weight: 700;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #333;
                font-weight: 500;
            }
            input[type="text"], input[type="email"], input[type="password"] {
                width: 100%;
                padding: 0.75rem;
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            input[type="text"]:focus, input[type="email"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: #4a6fa5;
            }
            .submit-btn {
                width: 100%;
                padding: 0.75rem;
                background: #4a6fa5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }
            .submit-btn:hover {
                background: #3a5a95;
            }
            .login-link {
                text-align: center;
                margin-top: 1.5rem;
            }
            .login-link a {
                color: #4a6fa5;
                text-decoration: none;
            }
            .error {
                color: #e74c3c;
                font-size: 0.9rem;
                margin-top: 0.5rem;
            }
        </style>
    </head>
    <body>
        <div class="register-container">
            <div class="logo">
                <h1>NeuroLM</h1>
                <p>Create Your Account</p>
            </div>
            <form action="/register" method="post" onsubmit="return validateForm()">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <div class="form-group">
                    <label for="confirm_password">Confirm Password:</label>
                    <input type="password" id="confirm_password" name="confirm_password" required>
                    <div id="password-error" class="error" style="display: none;">Passwords do not match</div>
                </div>
                <button type="submit" class="submit-btn">Create Account</button>
            </form>
            <div class="login-link">
                <p>Already have an account? <a href="/login">Sign in here</a></p>
            </div>
        </div>
        
        <script>
            function validateForm() {
                const password = document.getElementById('password').value;
                const confirmPassword = document.getElementById('confirm_password').value;
                const errorDiv = document.getElementById('password-error');
                
                if (password !== confirmPassword) {
                    errorDiv.style.display = 'block';
                    return false;
                }
                errorDiv.style.display = 'none';
                return true;
            }
        </script>
    </body>
    </html>
    """)

@app.post("/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Handle user registration"""
    # Validate passwords match
    if password != confirm_password:
        return HTMLResponse("""
        <script>
            alert('Passwords do not match');
            window.location.href = '/register';
        </script>
        """)
    
    # Hash password and create user
    password_hash = hash_password(password)
    success = create_user_in_db(username, email, password_hash)
    
    if not success:
        return HTMLResponse("""
        <script>
            alert('Username already exists. Please choose a different username.');
            window.location.href = '/register';
        </script>
        """)
    
    # Redirect to login page
    return HTMLResponse("""
    <script>
        alert('Account created successfully! Please log in.');
        window.location.href = '/login';
    </script>
    """)

@app.get("/login")
async def login_page():
    """Serve login page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NeuroLM - Login</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
            }
            .login-container {
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
            }
            .logo {
                text-align: center;
                margin-bottom: 2rem;
            }
            .logo h1 {
                color: #4a6fa5;
                margin: 0;
                font-size: 2rem;
                font-weight: 700;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #333;
                font-weight: 500;
            }
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 0.75rem;
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            input[type="text"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: #4a6fa5;
            }
            .submit-btn {
                width: 100%;
                padding: 0.75rem;
                background: #4a6fa5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }
            .submit-btn:hover {
                background: #3a5a95;
            }
            .register-link {
                text-align: center;
                margin-top: 1.5rem;
            }
            .register-link a {
                color: #4a6fa5;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <h1>NeuroLM</h1>
                <p>Sign in to your account</p>
            </div>
            <form action="/login" method="post">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="submit-btn">Sign In</button>
            </form>
            <div class="register-link">
                <p>Don't have an account? <a href="/register">Create one here</a></p>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/login")
async def login_user(
    username: str = Form(...),
    password: str = Form(...)
):
    """Handle user login"""
    user_id = verify_user_login(username, password)
    
    if not user_id:
        return HTMLResponse("""
        <script>
            alert('Invalid username or password');
            window.location.href = '/login';
        </script>
        """)
    
    # Create session
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = {
        'user_id': user_id,
        'username': username
    }
    
    # Redirect to chat with session
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

# Serve the chat interface as the main page
@app.get("/")
async def serve_chat(request: Request):
    """Serve the chat interface"""
    # Check if user is logged in
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in user_sessions:
        return RedirectResponse(url="/login")
    
    return FileResponse("chat.html")

# Serve the memory management interface
@app.get("/memory")
async def serve_memory():
    """Serve the memory management interface"""
    return FileResponse("index.html")

# Chat models
class ChatMessage(BaseModel):
    message: str
    model: Optional[str] = "gpt-4o-mini"

class ChatResponse(BaseModel):
    response: str
    memory_stored: bool
    context_used: int

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_memory(chat_request: ChatMessage, request: Request):
    """
    Chat with LLM using memory system for context
    """
    try:
        # Extract user_id from session
        user_id = request.session.get("user_id")
        print(f"DEBUG: user_id from session: {user_id}")
        
        # Retrieve relevant memories for context
        retrieve_request = RetrieveMemoryRequest(
            query=chat_request.message,
            context=None,
            depth=5
        )
        
        # Get memory system instance
        memory_system = MemorySystem()
        relevant_memories = memory_system.retrieve_memories(
            query=chat_request.message,
            context="",
            depth=5,
            user_id=user_id
        )
        
        # Debug logging
        print(f"DEBUG: Query: {chat_request.message}")
        print(f"DEBUG: Retrieved {len(relevant_memories) if relevant_memories else 0} memories")
        if relevant_memories:
            for i, mem in enumerate(relevant_memories[:3]):
                print(f"DEBUG: Memory {i+1}: {mem.content[:100]}...")
        
        # Build context from memories
        context = ""
        if relevant_memories:
            context = "\n".join([f"Memory: {mem.content}" for mem in relevant_memories[:3]])
        
        # Call LLM with context
        system_prompt = f"""You are NeuroLM, an AI with access to your memory system. 
        
Relevant memories:
{context}

Respond naturally to the user's message, incorporating relevant memories when helpful."""

        # Store user message in memory
        user_memory_id = memory_system.add_memory(f"User said: {chat_request.message}", user_id=user_id)
        
        # Create LLM messages with memory context
        system_message = {
            "role": "system",
            "content": f"""You are NeuroLM, an AI with access to your memory system. You function as a thoughtful, supportive friend who speaks honestly and maintains engaging conversations.

Relevant memories from previous conversations:
{context}

Use these memories naturally in your responses when relevant. Be conversational, warm, and helpful."""
        }
        
        user_message = {
            "role": "user", 
            "content": chat_request.message
        }
        
        messages = [system_message, user_message]
        
        # Generate LLM response
        from model_service import ModelService
        model_service = ModelService()
        
        try:
            response_text = await model_service.chat_completion(
                messages=messages,
                model=chat_request.model or "openai/gpt-4o-mini"
            )
        except Exception as e:
            # Fallback response if LLM fails
            response_text = f"I understand your message about '{chat_request.message}'. "
            if relevant_memories:
                response_text += f"This connects to {len(relevant_memories)} memories I have. "
            response_text += "I'm having trouble generating a full response right now."
        
        # Store assistant response in memory
        assistant_memory_id = memory_system.add_memory(f"Assistant responded: {response_text}", user_id=user_id)
        
        return ChatResponse(
            response=response_text,
            memory_stored=True,
            context_used=len(relevant_memories) if relevant_memories else 0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Clear database endpoint
@app.post("/api/clear-memory")
async def clear_memory_database():
    """Clear all data from Neo4j database"""
    try:
        memory_system = MemorySystem()
        with memory_system.driver.session() as session:
            # Delete all nodes and relationships
            session.run("MATCH (n) DETACH DELETE n")
            
        return {"status": "success", "message": "All memory data cleared from database"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")

# Get all available models from OpenRouter
@app.get("/api/models")
async def get_available_models():
    """Get all available models from OpenRouter"""
    try:
        from model_service import ModelService
        model_service = ModelService()
        models = model_service.get_models()
        # Sort alphabetically by name
        models.sort(key=lambda x: x.get('name', '').lower())
        return models
    except Exception as e:
        # Return basic models if OpenRouter is unavailable
        default_models = [
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "description": "Fast and efficient model for general chat"},
            {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "description": "Google's latest fast model"}
        ]
        return default_models

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {"status": "healthy", "service": "NeuroLM Memory System"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)