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

### Advanced Memory Intelligence
- **Weighted Scoring Algorithm**: Multi-factor relevance calculation combining vector similarity (40%), temporal relevance (25%), access frequency (20%), and association strength (15%)
- **Dynamic Memory Consolidation**: Automatic strengthening of frequently accessed memories and pruning of weak, inactive ones
- **Multi-hop Association Discovery**: Finds indirect connections between memories through relationship chains
- **Contextual Memory Clustering**: Groups semantically related memories for enhanced retrieval
- **Temporal Decay Mechanisms**: Older memories naturally weaken unless reinforced through usage
- **Background Processing**: Nightly consolidation and hourly association maintenance

## Technology Stack

- **Frontend**: Streamlit web application with professional dark theme
- **AI Integration**: OpenRouter API for intelligent responses and topic extraction
- **Database**: Neo4j graph database with 384-dimensional vector embeddings
- **Memory Architecture**: Modular system with retrieval.py, consolidation.py, and association.py
- **Authentication**: Multi-user system with secure password hashing and session management
- **Background Services**: Scheduled consolidation and association maintenance processes

## Advanced Memory Architecture

### Core Components
- **retrieval.py**: Weighted scoring algorithm with configurable parameters
- **consolidation.py**: Background memory strengthening and pruning system
- **association.py**: Multi-hop discovery and contextual clustering engine
- **config.py**: Central configuration for all memory parameters

### Memory Scoring Algorithm
```
Final Score = (Vector Similarity × 0.40) + 
              (Temporal Relevance × 0.25) + 
              (Access Frequency × 0.20) + 
              (Association Strength × 0.15)
```

### Database Schema
- **User Nodes**: Multi-user accounts with secure authentication
- **Memory Nodes**: Conversations with embeddings, confidence scores, and access tracking
- **Topic Nodes**: AI-extracted conversation subjects with usage statistics
- **CREATED Relationships**: User-memory ownership links
- **ASSOCIATED_WITH Relationships**: Memory-to-memory connections with strength values
- **ABOUT Relationships**: Memory-topic associations with relevance weights

### Intelligent Features
- **Dynamic Confidence**: Memory reliability evolves based on usage patterns
- **Associative Strengthening**: Co-accessed memories develop stronger connections
- **Temporal Decay**: Unused associations naturally weaken over time
- **Smart Pruning**: Automatic removal of weak, inactive memories after configurable periods
- **Context Clustering**: Groups related memories for enhanced retrieval performance

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
pip install streamlit neo4j openai sentence-transformers PyPDF2 docx2txt python-dotenv pytz schedule numpy
```

### Running the Application
```bash
streamlit run test_app_fixed.py --server.port 5000
```

## Advanced Memory System Features

### Competitive Advantages
- **Multi-Factor Scoring**: Unlike basic vector similarity systems, NeuroLM combines multiple intelligence factors
- **Self-Improving**: Background consolidation automatically optimizes memory networks
- **Association Discovery**: Multi-hop relationship detection finds indirect connections other systems miss
- **Configurable Intelligence**: Adjustable scoring weights allow fine-tuning for different use cases
- **Production Ready**: Robust error handling, fallback mechanisms, and performance optimization

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
├── test_app_fixed.py    # Main Streamlit application with advanced memory system
├── memory.py            # Core Neo4j memory management with background services
├── retrieval.py         # Advanced weighted memory retrieval algorithm
├── consolidation.py     # Background memory consolidation and maintenance
├── association.py       # Multi-hop association discovery engine
├── config.py            # Central configuration for memory parameters
├── utils.py             # Utility functions for text processing and embeddings
├── neo4j_test.py        # Database connection verification
├── topic_test.py        # Topic system diagnostics
├── clear_database.py    # Database maintenance utility
├── .env.example         # Environment variable template
└── README.md            # This documentation
```

## Performance & Scalability

### Memory System Performance
- **Batch Processing**: Handles consolidation in configurable batch sizes
- **Caching Layer**: LRU cache for frequently accessed memory objects
- **Optimized Queries**: Efficient Neo4j queries with proper indexing
- **Background Processing**: Non-blocking consolidation and maintenance
- **Fallback Mechanisms**: Graceful degradation when advanced features fail

### Configuration Options
- **Retrieval Weights**: Adjustable scoring algorithm parameters
- **Consolidation Settings**: Configurable pruning thresholds and schedules
- **Association Parameters**: Tunable relationship strength and decay rates
- **Performance Limits**: Batch sizes, cache limits, and query restrictions

## License

This project demonstrates advanced AI memory architectures and biomemetic computing concepts for educational and research purposes.