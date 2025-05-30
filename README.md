# NeuroLM - Neural Language Model with Persistent Memory

An advanced AI chat application that solves the context loss problem of traditional chatbots through intelligent memory management and document processing. Built with Neo4j graph database technology for true conversation continuity and knowledge persistence.

## The Problem with Traditional AI Chat

Traditional AI chatbots suffer from "goldfish memory" - every conversation starts from scratch, forcing users to constantly re-explain context, preferences, and background information. Uploaded documents are forgotten, previous insights are lost, and there's no learning continuity.

## NeuroLM's Solution

NeuroLM creates a persistent, evolving neural memory network that:
- Remembers every conversation permanently
- Processes and retains uploaded documents as active knowledge
- Builds relationships between ideas across time
- Grows more intelligent with each interaction
- Provides true conversation continuity

## Core Features

### 🧠 Intelligent Memory System
- **Persistent Context**: Remembers conversations across sessions, weeks, or months
- **Graph-Based Architecture**: Neo4j database maps relationships between memories
- **Biomimetic Consolidation**: Strengthens important memories, weakens unused ones
- **Multi-Hop Discovery**: Finds connections between seemingly unrelated topics

### 🤖 Universal Model Access
- **Hundreds of AI Models**: Choose from OpenAI, Anthropic, Google, Meta, and more
- **Smart Model Selection**: Search and filter by capabilities, cost, context length
- **Cost Optimization**: Select the right model for each task and budget
- **Provider Independence**: Never locked into a single AI vendor

### 📄 Document Processing & Knowledge Integration
- **Multi-Format Support**: Process PDF, DOCX, Excel, CSV, and text files
- **Intelligent Chunking**: Breaks documents into semantic chunks with overlap
- **Persistent Knowledge**: Documents become permanent part of your AI's memory
- **Contextual Retrieval**: AI references document content in conversations naturally
- **Cross-Document Connections**: Links related information across multiple uploads

### 💬 Advanced Chat Experience
- **Conversation Continuity**: Pick up where you left off, even weeks later
- **Context-Aware Responses**: AI references previous discussions and documents naturally
- **Session Management**: Organized conversation history with smart grouping
- **Dynamic Learning**: System builds connections between conversations and documents

### 🔧 Technical Capabilities
- **Vector Embeddings**: Semantic similarity matching for intelligent retrieval
- **Association Networks**: Dynamic relationship discovery between concepts
- **Temporal Intelligence**: Memory strength evolves based on usage patterns
- **Background Optimization**: Automatic memory network enhancement

## Getting Started

### Prerequisites
- Neo4j Aura database (free tier available)
- OpenRouter API key (pay-per-use pricing)

### Environment Setup
Create `.env` file:
```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
OPENROUTER_API_KEY=your-openrouter-key
APP_USERNAME=your-username
APP_PASSWORD=your-password
```

### Installation
```bash
# Install dependencies
uv add streamlit neo4j openai requests python-dotenv PyPDF2 docx2txt openpyxl pandas

# Run application
streamlit run app.py --server.port 5000
```

## Competitive Advantages

### vs. Standard Chatbots
- **Memory Persistence**: Never lose conversation context
- **Relationship Mapping**: Understands connections between topics
- **Evolving Intelligence**: Gets smarter with each interaction

### vs. Enterprise Solutions
- **Personal Focus**: Designed for individual users, not teams
- **Accessible Pricing**: No enterprise licensing or setup costs
- **Simple Deployment**: Run anywhere, including personal servers

### vs. Memory-Enhanced AIs
- **True Graph Memory**: Not just vector similarity matching
- **Model Flexibility**: Choose optimal AI for each task
- **Open Architecture**: Full control over your data and deployment

## Use Cases

**For Professionals**
- Maintain context across long projects and meetings
- Reference previous decisions, strategies, and discussions
- Build cumulative knowledge bases from uploaded reports and documents
- Track project evolution and decision rationale over time

**For Researchers**
- Connect insights across research sessions and uploaded papers
- Maintain literature review context with document processing
- Track evolving hypotheses and findings with persistent memory
- Cross-reference uploaded research documents with conversations

**For Students & Learners**
- Accumulate knowledge from uploaded textbooks and course materials
- Connect concepts across different subjects and documents
- Track learning progress and build upon previous study sessions
- Create persistent study companions that remember your learning journey

**For Content Creators**
- Upload reference materials and maintain creative consistency
- Build upon previous creative decisions and character development
- Reference uploaded style guides, brand documents, and inspiration
- Develop long-term creative projects with continuous context

## Architecture

### Memory System
- **Neo4j Graph Database**: Stores memories as connected nodes
- **Vector Embeddings**: Semantic similarity for content matching
- **Temporal Scoring**: Time-based relevance weighting
- **Association Strength**: Relationship quality metrics

### Model Integration
- **OpenRouter API**: Access to 100+ AI models
- **Dynamic Selection**: Choose optimal model per conversation
- **Cost Transparency**: Clear pricing for each interaction
- **Provider Diversity**: Avoid vendor lock-in

### Background Processing
- **Memory Consolidation**: Strengthens frequently accessed information
- **Association Discovery**: Creates new connections between related memories
- **Pruning System**: Removes weak, outdated memories
- **Performance Optimization**: Maintains fast retrieval speeds

## Advanced Memory Features

### Weighted Scoring Algorithm
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
- **Smart Pruning**: Automatic removal of weak, inactive memories
- **Context Clustering**: Groups related memories for enhanced retrieval

## Technical Stack

- **Frontend**: Streamlit with custom neural-themed interface
- **Database**: Neo4j graph database for memory storage
- **AI Models**: OpenRouter API for multi-provider access
- **Embeddings**: Sentence-transformers for semantic understanding
- **Authentication**: Simple user management system
- **File Processing**: PDF/DOCX document handling

## File Structure

```
├── app.py                  # Main Streamlit application with chat interface
├── memory.py              # Core Neo4j memory management and neural processing
├── retrieval.py           # Advanced weighted memory retrieval algorithms
├── consolidation.py       # Background memory consolidation and optimization
├── association.py         # Multi-hop association discovery between memories
├── document_storage.py    # Neo4j document storage and retrieval system
├── document_ui.py         # Streamlit document upload and management interface
├── file_processor.py      # Multi-format document processing engine
├── model_service.py       # OpenRouter API model fetching and caching
├── simple_model_selector.py # Clean model selection dropdown interface
├── utils.py               # Utility functions for embeddings and text processing
├── config.py              # Central configuration management
├── .env.example           # Environment variable template
└── README.md              # Complete system documentation
```

## Performance & Scalability

### Memory System Performance
- **Batch Processing**: Handles consolidation in configurable batch sizes
- **Caching Layer**: Efficient model and memory caching
- **Optimized Queries**: Efficient Neo4j queries with proper indexing
- **Background Processing**: Non-blocking consolidation and maintenance
- **Fallback Mechanisms**: Graceful degradation when advanced features fail

### Configuration Options
- **Retrieval Weights**: Adjustable scoring algorithm parameters
- **Consolidation Settings**: Configurable pruning thresholds and schedules
- **Association Parameters**: Tunable relationship strength and decay rates
- **Model Selection**: Cached model lists with search functionality

## User Experience

### Interface Design
- **Professional Dark Theme**: Deep black backgrounds with pure white text
- **Clean Chat Layout**: Focus on natural conversation flow
- **Smart Model Selection**: Searchable dropdown with hundreds of AI models
- **Intuitive Navigation**: Simple sidebar with conversation history

### Conversation Features
- **New Chat Button**: Start fresh conversations anytime
- **Chat History**: Quick access to previous conversation sessions
- **Context Awareness**: AI remembers previous discussions for continuity
- **Model Flexibility**: Switch between AI models mid-conversation

## Future Roadmap

- **Mobile Application**: Native iOS/Android apps
- **Advanced Analytics**: Memory network visualization
- **Collaborative Features**: Shared memory spaces
- **API Access**: Programmatic memory interaction
- **Plugin System**: Third-party integrations

## Contributing

NeuroLM is designed to democratize advanced AI memory capabilities. Contributions welcome for:
- Memory algorithm improvements
- New model integrations
- Interface enhancements
- Performance optimizations

## License

Open source - designed to keep advanced AI memory accessible to everyone, not just enterprise users.

---

*NeuroLM: Where every conversation builds upon the last, creating an AI companion that truly learns with you.*