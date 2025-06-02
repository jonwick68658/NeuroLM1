# NeuroLM

An advanced AI chat application with intelligent memory processing capabilities, featuring a sophisticated Neo4j-based memory system that learns and remembers conversations over time.

## Features

- **Interactive Chat Interface**: Clean, professional web interface for natural AI conversations
- **Advanced Memory System**: Neo4j graph database for persistent memory storage and retrieval
- **Multiple AI Models**: Choose between GPT-4o Mini and Gemini 2.0 Flash via OpenRouter
- **Memory-Informed Responses**: AI responses use relevant memories from previous conversations
- **Real-time Learning**: Every conversation is stored and becomes part of the memory system
- **Memory Management**: Visual memory graph interface for exploring stored knowledge

## Technology Stack

- **Frontend**: Custom HTML/CSS with JavaScript for chat interface
- **Backend**: FastAPI for API endpoints and memory integration
- **Database**: Neo4j graph database with integrated vector storage
- **AI Models**: OpenRouter API (GPT-4o Mini, Gemini 2.0 Flash)
- **Embeddings**: OpenAI text-embedding-3-small for semantic similarity
- **Memory Architecture**: Unified Neo4j system (no ChromaDB dependency)

## Quick Start

1. **Environment Setup**:
   Set these environment variables:
   ```
   OPENROUTER_API_KEY=your_openrouter_key
   NEO4J_URI=your_neo4j_uri  
   NEO4J_USERNAME=your_username
   NEO4J_PASSWORD=your_password
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```

3. **Access the Interface**:
   - Chat Interface: `http://localhost:5000`
   - Memory Management: `http://localhost:5000/memory`

## Usage

### Chat Interface
- Start conversations that build persistent memory over time
- Choose between AI models using the dropdown selector
- View memory context information with each response

### Memory System
- Automatically stores all conversations in Neo4j
- Retrieves relevant memories to inform AI responses
- Builds semantic connections between related topics
- Maintains conversation history across sessions

## API Endpoints

- `POST /api/chat` - Send messages and receive AI responses
- `POST /api/memorize/` - Store new memories
- `POST /api/retrieve/` - Retrieve relevant memories
- `PUT /api/enhance/{memory_id}` - Enhance memory importance
- `PUT /api/forget/{memory_id}` - Remove specific memories
- `POST /api/clear-memory` - Clear all stored memories

## Architecture

### Memory System Core
- **Neo4j Integration**: Single database for both graph relationships and vector storage
- **Semantic Search**: OpenAI embeddings stored as node properties
- **Context Retrieval**: Relevant memories included in AI conversations
- **Automatic Learning**: Every interaction strengthens the memory network

### Chat Flow
1. User sends message
2. System retrieves relevant memories from Neo4j
3. Memories provide context to AI model
4. AI generates informed response
5. Both user message and response stored as new memories

## Development

Key components:
- `main.py` - FastAPI server and chat endpoints
- `memory.py` - Core memory system with Neo4j integration
- `memory_api.py` - Memory management API endpoints
- `model_service.py` - OpenRouter AI model integration
- `chat.html` - Chat interface frontend
- `index.html` - Memory management interface

## Memory Management

The system provides both automatic and manual memory management:
- **Automatic**: All conversations stored and retrieved seamlessly
- **Manual**: Memory enhancement, decay, and deletion through API
- **Visualization**: Graph interface to explore memory connections
- **Categories**: Automatic categorization of different memory types

This creates an AI that truly learns and remembers, becoming more helpful over time through accumulated conversational experience.