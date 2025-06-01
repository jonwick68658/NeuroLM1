# NeuroLM - Neural Language Model with Hierarchical Memory

An advanced AI chat application featuring a sophisticated neural memory system that organizes conversations using hierarchical topic-based architecture, mimicking human cognitive memory organization.

## Core Features

### Neural Memory System
- **Hierarchical Organization**: User → Topic → Memory structure that mirrors human memory
- **Multi-Topic Support**: Complex conversations automatically connected to multiple relevant topics
- **Semantic Retrieval**: Context-aware memory search using authentic OpenAI embeddings
- **Cross-Topic Linking**: Related memories connected across different topic categories
- **Topic Extraction**: Powered by Google Gemini 2.0 Flash with GPT-4o Mini fallback
- **Quality Memory Assessment**: Intelligent evaluation of memory context to trigger strategic questioning
- **Actionable Preference Focus**: Prioritizes specific, useful user patterns over general conversation

### AI Integration
- **OpenRouter Models**: Access to multiple AI models with dynamic selection
- **Default Model**: GPT-4o Mini for cost-effective conversations
- **Context Enhancement**: Memory-augmented responses using stored conversation history
- **Authentic Data Only**: System uses only real conversation data, no synthetic content
- **Strategic Questioning**: Intelligent prompting to extract actionable user preferences and patterns
- **Memory Density Assessment**: Evaluates context quality to trigger targeted memory building

### User Management
- **Secure Authentication**: Account creation and login with encrypted passwords
- **Individual Memory Spaces**: Each user maintains their own neural memory network
- **Session Management**: Persistent login states and user preferences

## Technology Stack

- **Frontend**: Streamlit web interface
- **Database**: Neo4j graph database for hierarchical memory storage
- **AI Models**: OpenRouter integration with OpenAI models
- **Embeddings**: OpenAI text-embedding-3-small for authentic semantic search
- **Topic Extraction**: Google Gemini 2.0 Flash for enhanced topic identification
- **Memory Architecture**: Topic-based hierarchical organization with collision detection

## Neural Memory Architecture

The system implements a biomimetic memory structure:

```
User Node
├── Topic: "Sports"
│   ├── Memory: "went to baseball game"
│   └── Memory: "love watching football"
├── Topic: "Family"
│   ├── Memory: "my son enjoys sports"
│   └── Memory: "planning family vacation"
└── Topic: "Fitness"
    ├── Memory: "morning workout routine"
    └── Memory: "need to exercise more"
```

### Multi-Topic Conversations
Complex messages are analyzed and connected to multiple relevant topics:
- Input: "Went to baseball game with my son after my morning workout"
- Topics Created: Sports, Family, Fitness
- Result: Single memory connected to all three topic nodes

## Getting Started

### Prerequisites
- Neo4j database instance
- OpenRouter API key
- OpenAI API key (for embeddings)

### Environment Variables
```
NEO4J_URI=your_neo4j_connection_string
NEO4J_USER=your_neo4j_username
NEO4J_PASSWORD=your_neo4j_password
OPENROUTER_API_KEY=your_openrouter_api_key
OPENAI_API_KEY=your_openai_api_key
```

### Running the Application
```bash
streamlit run app.py --server.port 5000
```

## Usage

### Basic Workflow
1. **Create Account**: Register with username, email, and password
2. **Start Conversation**: Begin chatting with the AI assistant
3. **Memory Building**: System automatically organizes your conversations by topics
4. **Context Retrieval**: AI accesses relevant memories to provide contextual responses
5. **Explore Memory**: View analytics to see how your conversations are organized

### Memory System Benefits
- **No Context Loss**: Conversations build upon previous discussions
- **Topic Organization**: Related conversations grouped intelligently
- **Semantic Search**: Find relevant information using natural language queries
- **Authentic Responses**: AI uses only actual conversation history, no fabricated details

## Neural Memory Features

### Automatic Topic Extraction
- Analyzes conversation content using Google Gemini 2.0 Flash with GPT-4o Mini fallback
- Extracts 1-3 most relevant topics per message
- Handles both simple and complex multi-topic conversations

### Hierarchical Storage
- Creates topic nodes for conversation categories
- Links individual memories to relevant topics
- Maintains relationships between users, topics, and memories

### Enhanced Retrieval with Quality Assessment
- Searches across all connected topics for relevant context
- Ranks memories by semantic similarity to current query
- Evaluates memory density to trigger strategic questioning
- Provides organized context grouped by topic areas
- Prioritizes actionable user preferences over general conversation

### Strategic Memory Building
- Detects sparse memory contexts to trigger targeted questioning
- Focuses on extracting specific, actionable user preferences
- Learns concrete patterns in how users like to work and communicate
- Builds understanding of user rules, constraints, and technology choices

## Project Structure

```
├── app.py                 # Main Streamlit application
├── neural_memory.py       # Core hierarchical memory system
├── simple_model_selector.py # AI model selection interface
├── model_service.py       # OpenRouter integration
├── utils.py              # Embedding and utility functions
└── README.md             # Documentation
```

## Key Components

### NeuralMemorySystem
- Topic extraction and management
- Multi-topic memory storage
- Semantic context retrieval
- Cross-topic relationship creation

### Model Integration
- OpenRouter API connectivity
- Dynamic model selection
- Cost-optimized default selection (GPT-4o Mini)

### Memory Analytics
- Topic distribution analysis
- Memory count tracking
- Neural network visualization
- Conversation pattern insights

## Memory System Design Principles

### Authenticity
- Uses only actual conversation data
- No synthetic or placeholder information
- Preserves exact user statements and AI responses

### Efficiency
- Optimized vector similarity search
- Targeted topic-based retrieval
- Minimal API calls through better context management

### Scalability
- Graph database architecture supports complex relationships
- Multi-topic connections enable rich semantic networks
- Hierarchical organization maintains performance with growth

## Development Notes

### Database Schema
The Neo4j database automatically creates:
- User nodes with authentication data
- Topic nodes with embeddings and metadata
- Memory nodes with conversation content and embeddings
- Relationships: HAS_TOPIC, CONTAINS_MEMORY, RELATES_TO

### Performance Considerations
- Vector embeddings enable fast semantic search
- Topic-based organization reduces search space
- Graph structure provides efficient relationship traversal

## Contributing

The neural memory system is designed for extensibility:
- Topic extraction can be enhanced with more sophisticated NLP
- Memory consolidation algorithms can be improved
- Additional relationship types can be added
- Analytics and visualization can be expanded

## License

MIT License - See LICENSE file for details.