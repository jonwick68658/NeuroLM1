# NeuroLM - Advanced AI Memory System

An intelligent AI chat system with integrated memory, topic organization, and personalized user management. Features semantic memory retrieval, conversation management, and intelligent context routing for optimal performance and organization.

## 🚀 DEPLOYMENT STATUS: READY
Production-ready with intelligent memory routing, Google Gemini 1M+ context support, and streamlined OpenRouter-only architecture.

## Features

- **Interactive Chat Interface**: Clean, responsive web interface with markdown rendering and unlimited input capacity
- **Intelligent Memory System**: Neo4j graph database with smart context retrieval and user isolation
- **Semantic Memory Routing**: AI-powered intent classification for optimal memory retrieval
- **Large Context Models**: Google Gemini models with 1M+ token context windows via OpenRouter
- **Memory-Informed Responses**: AI responses enhanced with relevant context from previous conversations
- **Rich Text Formatting**: Full markdown support with syntax highlighting and copy buttons
- **Real-time Learning**: Automatic importance scoring and fact extraction from conversations
- **User Authentication**: Secure registration and login system with session management
- **Conversation Management**: Topic organization, conversation deletion, and history browsing
- **File Upload System**: Direct file upload with AI integration and PostgreSQL storage

## Technology Stack

- **Frontend**: Custom HTML/CSS with JavaScript, responsive design, PWA support
- **Backend**: FastAPI with cookie-based authentication and async processing
- **Memory Database**: Neo4j graph database with vector embeddings and semantic search
- **User Database**: PostgreSQL for user data, conversations, and file storage
- **AI Integration**: OpenRouter API (Google Gemini, GPT-4o, Claude, Llama, etc.)
- **Embeddings**: OpenAI text-embedding-3-small for semantic similarity
- **Memory Architecture**: Intelligent routing with importance scoring and fact extraction
- **UI Features**: Progressive loading, mobile PWA, searchable model selector

## Quick Start

1. **Environment Setup**:
   Set these environment variables:
   ```
   OPENROUTER_API_KEY=your_openrouter_key
   OPENAI_API_KEY=your_openai_key
   NEO4J_URI=your_neo4j_uri  
   NEO4J_USER=your_neo4j_username
   NEO4J_PASSWORD=your_neo4j_password
   DATABASE_URL=your_postgresql_url
   ```

2. **Run the Application**:
   ```bash
   python main.py
   ```

3. **Access the Interface**:
   - Chat Interface: `http://localhost:5000`
   - Register a new account or login to start chatting

## Usage

### Chat Interface
- Start conversations that build persistent memory over time
- Select from Google Gemini (1M+ context), GPT-4o, Claude, and other models
- Multi-line text input with Shift+Enter support for complex messages
- Rich markdown formatting in AI responses with copy functionality
- View intelligent memory context with each response
- Upload files using the paperclip button for AI analysis and discussion
- Organize conversations by topics and subtopics
- Delete conversations with confirmation modal

### Intelligent Memory System
- AI-powered intent classification routes queries optimally
- Automatic importance scoring determines what to remember
- Semantic similarity search finds relevant context
- Fact extraction from conversations builds knowledge base
- User-isolated memory ensures privacy and personalization

## API Endpoints

### Chat & Memory
- `POST /api/chat` - Send messages and receive AI responses with memory context
- `GET /api/models` - Get available AI models from OpenRouter
- `POST /api/upload-file` - Upload files for AI analysis and storage
- `GET /api/user-files` - Get user's uploaded files

### Conversations
- `GET /api/conversations` - Get paginated conversation list
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations/{id}/messages` - Get conversation messages
- `PUT /api/conversations/{id}/topic` - Update conversation topic
- `DELETE /api/conversations/{id}` - Delete conversation and memories

### Topics & Organization
- `GET /api/topics` - Get user's topics and subtopics
- `POST /api/topics` - Create new topic
- `POST /api/topics/{topic}/subtopics` - Create subtopic

### User Management
- `POST /register` - User registration
- `POST /login` - User authentication
- `GET /api/user/name` - Get current user's name

## Architecture

### Intelligent Memory System
The core innovation is the intelligent memory routing system that combines:

1. **Intent Classification**: AI determines whether queries need memory retrieval
2. **Importance Scoring**: Multi-factor analysis decides what information to store
3. **Semantic Retrieval**: Vector embeddings find contextually relevant memories
4. **Fact Extraction**: Structured information extraction from conversations

### Memory Flow
1. User sends message to chat interface
2. Intent classifier determines if memory retrieval needed
3. If needed, semantic search finds relevant context from Neo4j
4. Context enhances AI model prompt for informed response
5. Importance scorer evaluates response for storage
6. Facts extracted and stored with embeddings in Neo4j

### Database Architecture
- **Neo4j Graph Database**: Stores memories with vector embeddings as node properties
- **PostgreSQL**: User accounts, conversations, file uploads, session management
- **Dual Storage**: Leverages strengths of both graph and relational databases

## Development

### Key Components
- `main.py` - FastAPI server with authentication and chat endpoints
- `intelligent_memory.py` - Core memory system with AI-powered routing
- `model_service.py` - OpenRouter API integration (Google Gemini, GPT-4o, etc.)
- `chat.html` - Responsive chat interface with PWA support
- `mobile.html` - Mobile-optimized progressive web app

### Memory Classes
- `MemoryRouter` - Intent classification for efficient routing
- `ImportanceScorer` - Multi-factor importance evaluation
- `IntelligentMemorySystem` - Main memory orchestration
- Vector index setup and semantic search integration

### Recent Improvements
- Removed Cerebras dependency for streamlined OpenRouter-only architecture
- Enhanced context formatting for better AI understanding
- Added conversation deletion with database cleanup
- Implemented Google Gemini support with 1M+ token context windows

## Deployment

The system is production-ready with:
- User authentication and session management
- Database migrations and setup automation
- Error handling and logging
- Mobile PWA support with offline capabilities
- Optimized container deployment

This creates an AI assistant that intelligently manages memory, learns from conversations, and provides contextually relevant responses while maintaining user privacy and data isolation.