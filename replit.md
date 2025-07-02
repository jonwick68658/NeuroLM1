# NeuroLM - Advanced AI Memory System

## Overview

NeuroLM is an intelligent AI chat system that combines the power of large language models with persistent memory capabilities. The system uses a hybrid architecture featuring graph-based memory storage (Neo4j), vector embeddings for semantic search, and relational storage (PostgreSQL) for user management and file handling. The application provides a web-based chat interface with PWA support and integrates with multiple AI models through OpenRouter.

## System Architecture

The application follows a FastAPI-based microservice architecture with the following key layers:

### Frontend Layer
- **Web Interface**: Custom HTML/CSS with vanilla JavaScript
- **Mobile PWA**: Progressive Web App with offline capabilities and service worker
- **Real-time Communication**: Direct HTTP API calls with streaming support
- **UI Components**: Responsive chat interface with markdown rendering, file upload, and model selection

### Backend Layer
- **API Server**: FastAPI application with session-based authentication
- **Memory System**: Intelligent memory routing with semantic similarity matching
- **Model Integration**: OpenRouter API integration supporting multiple AI providers
- **File Management**: PostgreSQL-based file storage and retrieval system

### Data Layer
- **Graph Database**: Neo4j for conversation memory and context relationships
- **Relational Database**: PostgreSQL for user accounts, sessions, and file storage
- **Vector Embeddings**: OpenAI text-embedding-3-small for semantic search
- **Session Storage**: In-memory session management with cookie-based authentication

## Key Components

### 1. Intelligent Memory System (`intelligent_memory.py`)
- **Memory Router**: Intent classification for optimal memory retrieval
- **Semantic Search**: Vector-based similarity matching for context recall
- **Graph Storage**: Neo4j nodes and relationships for conversation history
- **Fact Extraction**: Automated extraction and storage of important information
- **User Isolation**: Memory segmentation per user for privacy

### 2. Model Service (`model_service.py`)
- **OpenRouter Integration**: API wrapper for multiple AI model providers with web search support
- **Web Search Capability**: Real-time web data integration using OpenRouter's `:online` suffix
- **Model Management**: Dynamic model listing and selection
- **Request Handling**: Standardized chat completion interface
- **Error Handling**: Robust fallback mechanisms for API failures

### 3. Main Application (`main.py`)
- **FastAPI Server**: Core web application and API endpoints
- **Authentication**: Session-based user authentication system
- **File Upload**: Direct file handling with database storage
- **Chat Management**: Conversation persistence and retrieval
- **Static Serving**: Web assets and PWA manifest serving

### 4. Web Interface (`chat.html`, `mobile.html`)
- **Responsive Design**: Desktop and mobile-optimized interfaces
- **Real-time Chat**: Asynchronous message handling with streaming
- **Web Search Integration**: Toggle button (🌐) for enabling real-time web data access
- **Markdown Support**: Rich text rendering with syntax highlighting
- **PWA Features**: Offline support, installable app experience
- **File Integration**: Drag-and-drop file upload with AI integration

## Data Flow

### Chat Flow
1. User submits message through web interface
2. Session validation and user identification
3. Intelligent memory system retrieves relevant context
4. Combined prompt (message + context) sent to selected AI model via OpenRouter
5. AI response processed and displayed with markdown rendering
6. Conversation and response stored in Neo4j graph database
7. New facts extracted and embedded for future retrieval

### Memory Flow
1. Every user message generates vector embeddings
2. Embeddings stored in Neo4j with conversation context
3. Memory router classifies query intent (personal recall, factual, general)
4. Semantic search retrieves top-k relevant memories
5. Context augments AI prompt for informed responses
6. Response analysis extracts new facts for storage

### File Flow
1. Files uploaded through web interface or drag-and-drop
2. File content stored in PostgreSQL with metadata
3. File context made available to AI models for processing
4. Download endpoints provide secure file retrieval
5. File references integrated into conversation memory

## External Dependencies

### Required Services
- **Neo4j Database**: Graph database for memory storage (Neo4j Aura recommended)
- **PostgreSQL**: Relational database for user data and files
- **OpenRouter API**: AI model access and management
- **OpenAI API**: Text embeddings for semantic search

### Optional Services
- **Redis**: Session storage and caching (future enhancement)
- **Cloud Storage**: File storage alternative to PostgreSQL

### API Keys Required
- `OPENROUTER_API_KEY`: Access to AI models through OpenRouter
- `OPENAI_API_KEY`: Text embedding generation
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j database connection
- `DATABASE_URL`: PostgreSQL connection string

## Deployment Strategy

### Replit Deployment
- **Autoscale Target**: Configured for automatic scaling based on demand
- **Port Configuration**: FastAPI server on port 5000, external port 80
- **Environment**: Python 3.11 with PostgreSQL 16 support
- **Build Optimization**: Container size reduction with cache cleanup

### Production Considerations
- **Container Optimization**: Build script removes cache files and temporary data
- **Security**: Environment variables for all sensitive credentials
- **Scalability**: Stateless design allows horizontal scaling
- **Monitoring**: Error handling and logging throughout application

### Environment Setup
1. Copy `.env.example` to `.env` and configure credentials
2. Set up Neo4j Aura instance and obtain connection details
3. Configure PostgreSQL database (provided by Replit)
4. Obtain OpenRouter and OpenAI API keys
5. Run `python main.py` to start the application

## Memory Enhancement Implementation

### Phase 1: Daily Memory Summarization (COMPLETED)
- **Status**: Successfully implemented and tested
- **Features**: 
  - AI-powered daily conversation summarization
  - Enhanced memory retrieval combining raw memories and summaries
  - Intelligent importance scoring for memory storage
  - Comprehensive test suite with real user data validation
- **Performance**: Hybrid retrieval system provides richer context without performance impact

### Phase 2: Topic Clustering and Relationships (ABANDONED)
- **Status**: Abandoned due to performance constraints
- **Issue**: Sequential AI processing for topic extraction created unacceptable delays (20-30 seconds)
- **Decision**: Prioritized system stability and performance over advanced relationship mapping
- **Alternative**: Phase 1 daily summaries provide sufficient intelligent memory enhancement

## System Performance
- Memory retrieval: <100ms for vector search on 100+ memories
- Daily summarization: Background processing without user impact
- Context enhancement: Successful integration of summaries with raw memory data
- User experience: Maintained fast response times while adding intelligent memory capabilities

## Changelog

- July 1, 2025: Implemented ChatGPT-style floating input bubble with borderless design and content overlay effect
- July 1, 2025: Research completed on OpenAI Realtime API for future voice enhancement (postponed)
- June 30, 2025: Completed Phase 1 memory enhancement with daily summarization
- June 30, 2025: Abandoned Phase 2 relationship mapping due to performance issues
- June 24, 2025: Added OpenRouter web search integration with 🌐 button for real-time web data access
- June 24, 2025: Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.