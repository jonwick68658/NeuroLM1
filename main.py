from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from memory_api import *
import uvicorn
import os

# Create FastAPI application
app = FastAPI(title="NeuroLM Memory System", version="1.0.0")

# Include memory API routes
app.include_router(router, prefix="/api")

# Serve the custom HTML interface
@app.get("/")
async def serve_index():
    """Serve the custom HTML interface"""
    return FileResponse("index.html")

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {"status": "healthy", "service": "NeuroLM Memory System"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)