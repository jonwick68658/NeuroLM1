# NeuroLM - Neural Language Model

A sophisticated AI chat application with intelligent memory capabilities, featuring multi-user authentication and persistent conversation storage using Neo4j graph database technology.

## Features

### Core Functionality
- **Clean Chat Interface**: Professional dark-themed UI with natural conversation flow
- **Multi-User System**: Individual user accounts with email registration and secure authentication
- **Persistent Memory Storage**: All conversations stored in Neo4j with user isolation
- **Conversation History**: Interactive sidebar with recent chat sessions and easy navigation

### User Management
- **Secure Registration**: Email collection with username/password authentication
- **Data Isolation**: Complete separation between user accounts in database
- **User Profiles**: Personalized sidebar with username display and first letter avatar
- **Session Management**: Secure login/logout with persistent sessions

### Memory Intelligence
- **Vector Embeddings**: Semantic search using neural embeddings for context retrieval
- **Associative Memory**: Related conversations automatically link for enhanced context
- **Topic Organization**: AI-powered topic extraction and categorization
- **Conversation Continuity**: Access to previous discussions for context-aware responses

## Technology Stack

- **Frontend**: Streamlit web application with custom dark theme
- **AI Integration**: OpenRouter API for intelligent responses
- **Database**: Neo4j graph database with vector embeddings
- **Authentication**: Multi-user system with hashed passwords
- **Memory System**: Vector embeddings for semantic conversation retrieval

## Database Schema

### Nodes
- **User**: Individual user accounts with unique IDs
- **Memory**: Conversation entries with embeddings, confidence scores, and access tracking
- **Topic**: Automatically extracted conversation subjects with mention counts

### Relationships
- **CREATED**: Users create memories
- **ASSOCIATED_WITH**: Memories link to related conversations with strength scores
- **ABOUT**: Memories connect to relevant topics with relevance weights

## Memory Capabilities

### Biomemetic Properties
- **Learning**: Important memories strengthen through repeated access
- **Forgetting**: Unused memories gradually weaken (foundation implemented)
- **Association**: Related conversations form stronger neural pathways
- **Context Awareness**: Recent and frequently accessed memories boost retrieval

### Retrieval Intelligence
- **Vector Similarity**: Primary search using embedding comparisons
- **Temporal Relevance**: Recent conversations weighted higher
- **Frequency Bonus**: Often-accessed memories get retrieval priority
- **Associative Boost**: Connected memories enhance each other's relevance

## Installation & Setup

### Prerequisites
- Python 3.11+
- Neo4j Aura database instance
- OpenRouter API key

### Environment Variables
Create `.env` file with:
```
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
OPENROUTER_API_KEY=your-openrouter-key
```

### Dependencies
```bash
pip install streamlit neo4j openai sentence-transformers PyPDF2 docx2txt python-dotenv pytz
```

### Running the Application
```bash
streamlit run test_app_fixed.py --server.port 5000
```

## User Experience

### Interface Design
- **Professional Dark Theme**: Deep black backgrounds with pure white text for optimal readability
- **Clean Chat Layout**: Focus on natural conversation without distracting elements
- **Responsive Design**: Works seamlessly across desktop and mobile devices
- **Intuitive Navigation**: Simple sidebar with conversation history and user profile

### Conversation Features
- **New Chat Button**: Start fresh conversations anytime
- **Chat History**: Quick access to previous conversation sessions
- **Context Awareness**: AI remembers previous discussions for continuity
- **Natural Flow**: Clean message display without technical details

## Architecture Highlights

### Memory Storage
Each conversation is stored with:
- Vector embedding for semantic search
- Timestamp for temporal analysis
- Confidence score for reliability tracking
- Access count for importance weighting
- Topic relationships for categorization

### Associative System
Memories connect through:
- **Temporal Proximity**: Recent conversations link stronger
- **Content Similarity**: Shared vocabulary creates bonds
- **Topic Overlap**: Common subjects form connections
- **Access Patterns**: Frequently retrieved together

### Intelligence Features
- **Context Building**: Relevant memories enhance AI responses
- **Learning Adaptation**: System improves through usage patterns
- **Relationship Mapping**: Conversations form meaningful networks
- **Topic Discovery**: Automatic identification of discussion themes

## Future Development Roadmap

### Planned Enhancements
- **Document Upload**: Feed external knowledge into memory system
- **Advanced Forgetting**: Automatic pruning of weak memories
- **Memory Consolidation**: Background processing for connection strengthening
- **Visual Network Maps**: Interactive graph visualization of memory connections
- **Export Capabilities**: Backup and share memory networks

### Biomemetic Improvements
- **Emotional Weighting**: Sentiment analysis for memory importance
- **Contradiction Detection**: Identify conflicting information
- **Knowledge Synthesis**: Combine related memories for insights
- **Temporal Memory Decay**: More sophisticated forgetting algorithms

## File Structure

```
├── test_app_fixed.py    # Main Streamlit application with multi-user support
├── memory.py            # Neo4j memory management system
├── utils.py             # Utility functions for text processing and embeddings
├── neo4j_test.py        # Database connection verification
├── topic_test.py        # Topic system diagnostics
├── clear_database.py    # Database maintenance utility
├── .env.example         # Environment variable template
└── README.md            # This documentation
```

## License

This project demonstrates advanced AI memory architectures and biomemetic computing concepts for educational and research purposes.