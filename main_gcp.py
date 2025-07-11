"""
NeuroLM Main Application - GCP Version
Supports both Neo4j and PostgreSQL backends based on environment variables
"""

import os
import sys
import asyncio
from typing import Dict, Optional

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your existing main app
from main import app, create_user_in_db, verify_user_login, get_user_first_name
from main import get_session, create_session, delete_session, cleanup_expired_sessions
from main import get_authenticated_user, init_file_storage, get_db_connection
from main import store_user_tool, get_user_tools, update_tool_usage

# Import the dual memory system
from intelligent_memory_dual import DualIntelligentMemorySystem

# Override the intelligent memory system with dual backend
print("🚀 Starting NeuroLM GCP version...")
print(f"🔧 Backend mode: {'PostgreSQL' if os.getenv('USE_POSTGRESQL') == 'true' else 'Neo4j'}")

# Replace the global intelligent memory system
intelligent_memory_system = DualIntelligentMemorySystem()

# Override the import in main.py
import main
main.intelligent_memory_system = intelligent_memory_system

# Background RIAI service
background_riai_service = None

async def startup_event():
    """Initialize background services"""
    global background_riai_service
    
    print("🔧 Initializing memory system...")
    backend_info = intelligent_memory_system.get_backend_info()
    print(f"✅ Memory backend: {backend_info['backend']}")
    
    # Initialize PostgreSQL connection pool if using PostgreSQL
    if backend_info['backend'] == 'postgresql':
        await intelligent_memory_system.active_system.initialize_pool()
        print("✅ PostgreSQL connection pool initialized")
    
    # Initialize database tables
    try:
        init_file_storage()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"⚠️  Database table initialization: {e}")
    
    # Start background RIAI service
    try:
        from background_riai import BackgroundRIAIService
        background_riai_service = BackgroundRIAIService()
        await background_riai_service.start_background_service()
        print("✅ Background RIAI service started")
    except Exception as e:
        print(f"⚠️  Background RIAI service: {e}")

async def shutdown_event():
    """Clean up background services"""
    global background_riai_service
    
    if background_riai_service:
        background_riai_service.stop_background_service()
        print("✅ Background RIAI service stopped")
    
    if intelligent_memory_system:
        intelligent_memory_system.close()
        print("✅ Memory system closed")

# Override the startup/shutdown events
from main import app as original_app

# Remove existing event handlers
original_app.router.lifespan = None

# Add new lifespan handler
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()

app.router.lifespan = lifespan

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    backend_info = intelligent_memory_system.get_backend_info()
    return {
        "status": "healthy",
        "backend": backend_info['backend'],
        "version": "gcp-1.0"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)