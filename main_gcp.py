"""
NeuroLM Main Application - GCP Version
Uses PostgreSQL backend for memory management
"""

import os
import sys
import asyncio
from typing import Dict, Optional
from contextlib import asynccontextmanager

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the dual memory system
from intelligent_memory_dual import DualIntelligentMemorySystem

# Initialize the memory system
print("🚀 Starting NeuroLM GCP version...")
print(f"🔧 Backend mode: PostgreSQL")

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
        try:
            await intelligent_memory_system.active_system.initialize_pool()
            print("✅ PostgreSQL connection pool initialized")
        except Exception as e:
            print(f"⚠️  PostgreSQL connection pool: {e}")
    
    # Initialize database tables
    try:
        from main import init_file_storage
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

# Use proper lifespan context manager
@asynccontextmanager
async def lifespan(app):
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()

# Import the main app and set lifespan properly
from main import app
app.router.lifespan = lifespan

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)