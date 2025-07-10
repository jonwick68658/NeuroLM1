-- NeuroLM GCP PostgreSQL Setup Commands
-- Run these commands once your Cloud SQL instance is created

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the main database schema
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    topic VARCHAR(255),
    sub_topic VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- 3. Create the intelligent memory table with vector support
CREATE TABLE IF NOT EXISTS intelligent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    conversation_id VARCHAR(255),
    message_id INTEGER,
    content TEXT NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    embedding vector(1536),
    importance FLOAT,
    quality_score FLOAT,
    evaluation_timestamp TIMESTAMP,
    evaluation_model VARCHAR(100),
    human_feedback_score FLOAT,
    human_feedback_type VARCHAR(50),
    human_feedback_timestamp TIMESTAMP,
    final_quality_score FLOAT,
    final_score_timestamp TIMESTAMP,
    uf_score_awarded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
);

-- 4. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_intelligent_memories_user_id ON intelligent_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_intelligent_memories_conversation_id ON intelligent_memories(conversation_id);
CREATE INDEX IF NOT EXISTS idx_intelligent_memories_message_type ON intelligent_memories(message_type);
CREATE INDEX IF NOT EXISTS idx_intelligent_memories_quality_score ON intelligent_memories(quality_score);
CREATE INDEX IF NOT EXISTS idx_intelligent_memories_created_at ON intelligent_memories(created_at);

-- 5. Create HNSW index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_intelligent_memories_embedding_hnsw 
ON intelligent_memories USING hnsw (embedding vector_cosine_ops);

-- 6. Create other supporting tables
CREATE TABLE IF NOT EXISTS user_files (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),
    file_size INTEGER,
    content BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_tools (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    function_code TEXT NOT NULL,
    schema_json TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS subtopics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    topic_name VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, topic_name, name)
);

CREATE TABLE IF NOT EXISTS memory_topic_links (
    id SERIAL PRIMARY KEY,
    memory_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    linked_topic VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (memory_id) REFERENCES intelligent_memories(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 7. Create indexes for supporting tables
CREATE INDEX IF NOT EXISTS idx_user_files_user_id ON user_files(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tools_user_id ON user_tools(user_id);
CREATE INDEX IF NOT EXISTS idx_topics_user_id ON topics(user_id);
CREATE INDEX IF NOT EXISTS idx_subtopics_user_id ON subtopics(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_topic_links_user_id ON memory_topic_links(user_id);

-- 8. Verify pgvector installation
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 9. Test vector operations
SELECT '1,2,3'::vector <-> '1,2,4'::vector as cosine_distance;