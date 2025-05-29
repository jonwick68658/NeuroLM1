# Second Brain AI

A sophisticated AI chat application with biomemetic memory capabilities, leveraging Neo4j graph database technology for intelligent conversation storage, retrieval, and associative linking.

## Features

### Core Functionality
- **Intelligent Chat Interface**: Clean Streamlit-based UI with streaming AI responses
- **Persistent Memory Storage**: All conversations permanently stored in Neo4j Aura cloud database
- **Secure Authentication**: Login system with environment-based credentials

### Advanced Memory System
- **Memory Reinforcement**: Frequently accessed memories become stronger over time
- **Associative Linking**: Related conversations automatically connect through semantic similarity
- **Confidence Scoring**: Each memory has a reliability score that evolves with usage
- **Access Tracking**: System monitors how often memories are retrieved and referenced

### Topic Intelligence
- **Hybrid Topic Detection**: Uses OpenRouter API with keyword extraction fallback
- **Automatic Categorization**: Conversations organized by 2-3 main topics per message
- **Topic Networking**: Memories with shared topics form stronger connections
- **Topic Analytics**: Dashboard shows most discussed subjects and frequency

### Neural Network Visualization
- **Connection Mapping**: View total links between memories
- **Strength Analysis**: Monitor average connection strength across your knowledge base
- **Growth Tracking**: Watch your neural network evolve from basic to highly connected

## Technology Stack

- **Frontend**: Streamlit web application
- **AI Integration**: OpenRouter GPT-4o-mini for responses and topic extraction
- **Database**: Neo4j Aura cloud database with vector embeddings
- **Vector Search**: 384-dimensional embeddings with cosine similarity
- **Authentication**: Environment variable-based secure login

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
APP_USERNAME=your-username
APP_PASSWORD=your-password
```

### Dependencies
```bash
pip install streamlit neo4j openai sentence-transformers PyPDF2 docx2txt python-dotenv pytz
```

### Running the Application
```bash
streamlit run test_app.py --server.port 5000
```

## Current Statistics

Based on recent analysis:
- **Memory Nodes**: 30+ conversation entries stored
- **Topic Nodes**: 4 discovered topics
- **Neural Connections**: 24+ associative relationships
- **Connection Types**: Temporal, semantic, and topic-based linking

## Dashboard Metrics

### Core Memory
- Total Memories: Complete conversation count
- Strong Memories: Frequently accessed entries (3+ accesses)
- Average Confidence: Overall memory reliability percentage
- Total Accesses: Cumulative retrieval count across all memories

### Neural Connections
- Total Links: Number of associative relationships
- Strong Links: High-strength connections (70%+ strength)
- Link Strength: Average connection strength percentage
- Connectivity Status: Brain development indicator

### Topic Intelligence
- Total Topics: Number of discovered conversation subjects
- Top Topics: Most frequently discussed subjects with counts
- Topic Evolution: How conversation themes develop over time

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
├── test_app.py          # Main Streamlit application
├── memory.py            # Neo4j memory management system
├── utils.py             # Utility functions for text processing
├── neo4j_test.py        # Database connection verification
├── topic_test.py        # Topic system diagnostics
├── .env.example         # Environment variable template
└── README.md            # This documentation
```

## License

This project demonstrates advanced AI memory architectures and biomemetic computing concepts for educational and research purposes.