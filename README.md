# NeuroLM - Advanced AI Memory System

An intelligent AI chat system with topic-scoped memory search, conversation organization, and user-controlled memory linking. Features efficient memory retrieval, topic isolation, and cross-topic connection capabilities for optimal performance and context management.

## 🚀 DEPLOYMENT STATUS: READY
Container optimized from 8+ GiB to deployment-ready size through strategic exclusions while preserving complete Neo4j memory functionality.

## Features

### Core Chat Interface
- **Interactive Chat Interface**: Clean, professional web interface with markdown rendering and unlimited input capacity
- **Topic-Scoped Conversations**: Organize conversations by topics and sub-topics for better memory isolation
- **Complete Model Selection**: Searchable dropdown with all 323+ OpenRouter AI models including Cerebras, GPT, Claude, and Gemini
- **Rich Text Formatting**: Full markdown support with syntax highlighting and copy buttons
- **Mobile PWA Support**: Responsive design with Progressive Web App capabilities

### Advanced Memory System
- **Topic-Scoped Memory Search**: Memories are isolated by topic, eliminating inefficient full-system searches
- **User-Controlled Memory Linking**: `/link [topic]` command to create connections between topic memories
- **Hierarchical Search Strategy**: Conversation → Topic → Related Topics → Explicit Full Search
- **Memory Reinforcement**: Linked memories receive decay protection to preserve important connections
- **User-Isolated Storage**: Neo4j graph database with complete user authentication and memory isolation

### File Management & Slash Commands
- **File Upload System**: Direct file upload with paperclip button, PostgreSQL storage, and AI file access
- **Slash Command System**: `/files`, `/view`, `/delete`, `/search`, `/topics`, `/link`, `/unlink` commands
- **Topic Management**: Create and organize topics and sub-topics for better conversation structure

## Technology Stack

- **Frontend**: Custom HTML/CSS with JavaScript, Marked.js for markdown rendering, PWA support
- **Backend**: FastAPI with cookie-based authentication and topic-scoped memory retrieval
- **Database**: Neo4j graph database with topic-scoped vector storage + PostgreSQL for conversations and file storage
- **AI Models**: OpenRouter API with 323+ models (Cerebras, GPT, Claude, Gemini, Llama, Mistral, etc.)
- **Embeddings**: OpenAI text-embedding-3-small for semantic similarity within topic boundaries
- **Memory Architecture**: Topic-isolated Neo4j system with user-controlled linking and memory reinforcement
- **File System**: PostgreSQL storage with slash command interface for file management
- **Search Strategy**: Hierarchical memory search (conversation → topic → linked → explicit full)

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

### Topic-Scoped Conversations
- **Create Topics**: Organize conversations by topics (e.g., "Programming", "Cooking", "Personal")
- **Add Sub-topics**: Further categorize with sub-topics for precise organization
- **Memory Isolation**: Each topic maintains its own memory scope, preventing cross-contamination
- **Search Efficiency**: Memories are searched within current topic only, eliminating full-system searches

### Memory Linking System
- **Link Memories**: Use `/link [topic]` to connect current message to another topic's memories
- **Unlink Topics**: Use `/unlink [topic]` to remove connections between topics
- **Supplemental Context**: Linked memories provide gentle cross-topic awareness without flooding
- **Decay Protection**: Linked memories receive reinforcement to prevent loss over time

### Chat Interface Features
- **Smart Memory Retrieval**: Hierarchical search (conversation → topic → linked → explicit full)
- **Model Selection**: Search and select from 323+ AI models with autocomplete dropdown
- **Rich Formatting**: Multi-line input with Shift+Enter, markdown responses with copy functionality
- **Slash Commands**: `/files`, `/view`, `/delete`, `/search`, `/topics`, `/link`, `/unlink`
- **File Management**: Upload and analyze files with integrated AI access

## API Endpoints

### Chat & Memory
- `POST /api/chat` - Send messages with topic-scoped memory retrieval
- `POST /api/conversations/new` - Create new conversation with topic assignment
- `GET /api/conversations/{id}/messages` - Retrieve conversation messages with pagination
- `PUT /api/conversations/{id}/topic` - Update conversation topic and sub-topic

### Memory Management
- `POST /api/memorize/` - Store memories with topic context
- `POST /api/retrieve/` - Retrieve memories with hierarchical search
- `PUT /api/enhance/{memory_id}` - Reinforce memory importance
- `DELETE /api/forget/{memory_id}` - Remove specific memories
- `POST /api/clear-memory` - Clear all stored memories

### File & Topic Management
- `POST /api/upload-file` - Upload files with PostgreSQL storage
- `GET /api/user-files` - List user files with search capability
- `GET /api/download/{filename}` - Download user files
- `GET /api/topics` - Retrieve all user topics and sub-topics
- `POST /api/topics` - Create new topic
- `POST /api/topics/{topic}/subtopics` - Create sub-topic under existing topic

## Architecture

### Topic-Scoped Memory System
- **Hierarchical Search**: Conversation → Topic → Linked → Explicit Full search strategy
- **Memory Isolation**: Topics maintain separate memory boundaries to prevent cross-contamination
- **User-Controlled Linking**: `/link [topic]` creates connections between topic memories
- **Neo4j Integration**: Graph database stores memories with topic context and user isolation
- **PostgreSQL Storage**: Conversations, files, and memory links stored in relational database

### Enhanced Chat Flow
1. User sends message in topic-scoped conversation
2. System retrieves memories from current topic scope
3. Linked memories added as supplemental context (if any)
4. AI generates response using topic-relevant context
5. Both user message and response stored with topic metadata
6. Memory links created if `/link [topic]` command used

## Deployment Optimizations Applied

### Container Size Reduction (8+ GiB → <2 GiB)
- **Cache Exclusion**: .dockerignore prevents inclusion of .cache, .uvm, __pycache__ directories
- **Asset Optimization**: 535KB PNG icon replaced with 560-byte SVG (99.9% reduction)  
- **Dependency Cleanup**: Removed unused psycopg2-pool dependency
- **Development File Exclusion**: Git history, build artifacts, and attached assets excluded

### Topic-Scoped Memory Enhancements
- **Efficient Search**: Topic boundaries eliminate inefficient full-system memory searches
- **User-Controlled Linking**: Cross-topic connections only when explicitly requested by users
- **Memory Reinforcement**: Linked memories receive decay protection to preserve important connections
- **Hierarchical Strategy**: Smart search progression from conversation to topic to linked memories

## Development

### Key Components
- `main.py` - FastAPI server with topic-scoped chat endpoints and memory linking
- `memory.py` - Topic-aware memory system with hierarchical search and linking support
- `memory_api.py` - Memory management API with topic context
- `model_service.py` - OpenRouter AI model integration with 323+ models
- `chat.html` - Enhanced chat interface with slash commands and topic management
- `mobile.html` - Progressive Web App interface for mobile devices
- Database schema includes `memory_links` table for cross-topic connections

### Memory Management Features
- **Topic Isolation**: Memories automatically scoped to conversation topics
- **Smart Linking**: `/link [topic]` and `/unlink [topic]` commands for user-controlled connections
- **Decay Protection**: Linked memories reinforced to prevent important information loss
- **Slash Commands**: Comprehensive file and memory management through chat interface
- **Search Efficiency**: Eliminates full-system searches while maintaining context awareness

This creates an AI that learns within organized topic boundaries while allowing users to create meaningful connections between different areas of knowledge, resulting in both efficient performance and rich contextual understanding.