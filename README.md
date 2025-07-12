# NeuroLM - Self-Improving AI with Unlimited Context

An advanced AI chat system featuring recursive intelligence, unlimited context memory, and self-improvement capabilities. Built for high performance and scalability.

## Features

### 🧠 **Intelligent Memory System**
- Unlimited context per user with semantic search
- Vector-based memory storage using PostgreSQL + pgvector
- Quality-boosted retrieval for enhanced accuracy
- Automatic importance scoring and memory optimization

### 🔄 **Self-Improving AI (RIAI)**
- Recursive Intelligence Artificial Intelligence system
- AI self-evaluation and quality scoring
- Human feedback integration with advanced weighting
- Background processing for continuous improvement

### 🚀 **High Performance**
- PostgreSQL backend optimized for millions of users
- Asynchronous processing with FastAPI
- Vector similarity search with sub-100ms response times
- Efficient memory management and caching

### 🤖 **Multi-Model Integration**
- OpenRouter API with 200+ AI models
- Real-time web search integration
- Streaming responses for instant feedback
- Model selection and switching capabilities

### 📱 **Modern Interface**
- Progressive Web App (PWA) with offline support
- Mobile-responsive design with floating chat interface
- Dark/light theme with glass morphism effects
- File upload and processing capabilities

### 🔐 **Enterprise Security**
- Database-persistent session management
- Secure authentication and user isolation
- Environment-based configuration
- Production-ready deployment architecture

## Architecture

### **Backend Stack**
- **API Server**: FastAPI with async processing
- **Database**: PostgreSQL 16+ with pgvector extension
- **Memory System**: Vector embeddings with semantic search
- **AI Integration**: OpenRouter API for multiple model access
- **Background Services**: RIAI evaluation and processing

### **Frontend Stack**
- **Web Interface**: Vanilla JavaScript with modern ES6+
- **PWA Features**: Service worker, offline support, installable
- **Responsive Design**: Mobile-first with desktop optimization
- **Real-time Updates**: WebSocket-like streaming responses

### **Data Flow**
1. User messages processed through intelligent memory system
2. Semantic search retrieves relevant context
3. AI models generate responses with unlimited context
4. RIAI system evaluates and improves response quality
5. Background services continuously enhance memory quality

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- OpenRouter API key
- OpenAI API key (for embeddings)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jonwick68658/NeuroLM1.git
   cd NeuroLM1
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database configuration
   ```

4. **Set up database**
   ```bash
   # PostgreSQL with pgvector extension required
   # Database tables will be created automatically
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Access the application**
   - Open http://localhost:5000 in your browser
   - Create an account and start chatting

## Environment Variables

### Required
- `OPENROUTER_API_KEY`: OpenRouter API key for AI model access
- `OPENAI_API_KEY`: OpenAI API key for text embeddings
- `DATABASE_URL`: PostgreSQL connection string with pgvector
- `SECRET_KEY`: Session encryption key (generate with `openssl rand -hex 32`)

### Optional
- `REPLIT_DOMAIN`: Domain for Replit deployment
- `PORT`: Server port (default: 5000)

## Deployment

### **Replit Deployment**
- Configured for Replit Autoscale
- Automatic PostgreSQL database provisioning
- Environment variables managed through Replit Secrets
- Zero-configuration deployment

### **Production Deployment**
- Docker container support
- Cloud Run compatible
- Horizontal scaling ready
- Database migration handling

## Usage

### **Basic Chat**
1. Log in to your account
2. Start a new conversation
3. Experience unlimited context memory
4. Use the 🌐 button for web-enhanced responses

### **Advanced Features**
- **File Upload**: Drag and drop files for AI processing
- **Model Selection**: Choose from 200+ AI models
- **Feedback System**: Rate responses to improve AI quality
- **Memory Management**: Automatic context optimization

### **API Integration**
- RESTful API endpoints for integration
- Session-based authentication
- JSON response format
- Comprehensive error handling

## Performance

- **Memory Retrieval**: <100ms for semantic search
- **Response Generation**: Streaming for instant feedback
- **Background Processing**: Non-blocking RIAI evaluation
- **Scalability**: Designed for millions of concurrent users

## Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request
5. Ensure all tests pass

### Development Guidelines
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation as needed
- Maintain backward compatibility

## License

MIT License

Copyright (c) 2025 NeuroLM

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Support

For support, please:
- Check the documentation
- Search existing issues
- Create a new issue with detailed information
- Contact the development team

---

**NeuroLM** - Democratizing AI access through self-improving intelligence