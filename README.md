# NeuroLM

An advanced AI chat application with intelligent memory processing capabilities, featuring a sophisticated Neo4j-based memory system that learns and remembers conversations over time with complete user isolation and semantic relationship building.

## 🚀 DEPLOYMENT STATUS: READY
Container optimized from 8+ GiB to deployment-ready size through strategic exclusions while preserving complete Neo4j memory functionality.

## Features

- **Interactive Chat Interface**: Clean, professional web interface with markdown rendering and unlimited input capacity
- **User-Isolated Memory System**: Neo4j graph database with complete user authentication and memory isolation
- **Semantic Memory Relationships**: Automatic creation of RELATES_TO connections between similar memories
- **Complete Model Selection**: Searchable dropdown with all 323+ OpenRouter AI models
- **Memory-Informed Responses**: AI responses use relevant memories from previous conversations within user scope
- **Rich Text Formatting**: Full markdown support with syntax highlighting and copy buttons
- **Real-time Learning**: Every conversation builds semantic memory networks and strengthens relationships
- **User Authentication**: Secure registration and login system with session management
- **Memory Management**: Visual memory graph interface for exploring stored knowledge networks
- **File Upload System**: Direct file upload with paperclip button, PostgreSQL storage, and AI file access integration

## Technology Stack

- **Frontend**: Custom HTML/CSS with JavaScript, Marked.js for markdown rendering
- **Backend**: FastAPI with cookie-based authentication for secure user sessions
- **Database**: Neo4j graph database with vector storage and relationship mapping + PostgreSQL for file storage
- **AI Models**: OpenRouter API with 323+ models (GPT, Claude, Gemini, Llama, Mistral, etc.)
- **Embeddings**: OpenAI text-embedding-3-small for semantic similarity and relationship detection
- **Memory Architecture**: User-isolated Neo4j system with HAS_MEMORY and RELATES_TO relationships
- **File System**: PostgreSQL storage with direct AI access for uploaded documents
- **UI Features**: Unlimited input capacity, searchable model selector, markdown rendering with copy functionality

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

## Usage

### Chat Interface
- Start conversations that build persistent memory over time
- Search and select from 323+ AI models using the autocomplete dropdown
- Multi-line text input with Shift+Enter support for complex messages
- Rich markdown formatting in AI responses with copy functionality
- View memory context information with each response
- Upload files using the paperclip button for AI analysis and discussion

### Memory System
- Automatically stores all conversations in Neo4j
- Retrieves relevant memories to inform AI responses
- Builds semantic connections between related topics
- Maintains conversation history across sessions

## API Endpoints

- `POST /api/chat` - Send messages and receive AI responses
- `POST /api/upload-file` - Upload files for AI analysis and storage
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

## Deployment Optimizations Applied

### Container Size Reduction (8+ GiB → <2 GiB)
- **Cache Exclusion**: .dockerignore prevents inclusion of .cache, .uvm, __pycache__ directories
- **Asset Optimization**: 535KB PNG icon replaced with 560-byte SVG (99.9% reduction)  
- **Dependency Cleanup**: Removed unused psycopg2-pool dependency
- **Development File Exclusion**: Git history, build artifacts, and attached assets excluded

### Memory System Enhancements
- **Hybrid Retrieval**: Keyword-based search for name queries + semantic embeddings
- **User ID Debugging**: Proper user isolation with comprehensive logging
- **Context Preservation**: Neo4j memory system completely preserved and enhanced

## Development

Key components:
- `main.py` - FastAPI server and chat endpoints (36KB)
- `memory.py` - Core memory system with Neo4j integration (28KB)
- `memory_api.py` - Memory management API endpoints
- `model_service.py` - OpenRouter AI model integration
- `chat.html` - Chat interface frontend (embedded)
- `icon.svg` - Optimized application icon (560 bytes)
- `.dockerignore` - Container optimization configuration

## Memory Management

The system provides both automatic and manual memory management:
- **Automatic**: All conversations stored and retrieved seamlessly
- **Manual**: Memory enhancement, decay, and deletion through API
- **Visualization**: Graph interface to explore memory connections
- **Categories**: Automatic categorization of different memory types

This creates an AI that truly learns and remembers, becoming more helpful over time through accumulated conversational experience.