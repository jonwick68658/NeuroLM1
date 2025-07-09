from fastapi import FastAPI, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse, Response
from starlette.middleware.sessions import SessionMiddleware
# Memory API removed - using intelligent_memory directly
from pydantic import BaseModel
import uvicorn
import os
import httpx
import hashlib
import uuid
import psycopg2
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Use environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create FastAPI application
app = FastAPI(title="NeuroLM Memory System", version="1.0.0")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Router removed - simplified API structure

# Mount static files for PWA
app.mount("/static", StaticFiles(directory="static"), name="static")

# Session management now uses database only (migrated July 2, 2025)

# Database session management functions
def create_session(user_id: str, username: str, extended: bool = False) -> Optional[str]:
    """Create a new session in the database and return session_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        session_id = str(uuid.uuid4())
        # Extended session for 30 days if remember me is checked, otherwise 24 hours
        if extended:
            expires_at = datetime.now() + timedelta(days=30)
        else:
            expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute('''
            INSERT INTO sessions (session_id, user_id, username, expires_at)
            VALUES (%s, %s, %s, %s)
        ''', (session_id, user_id, username, expires_at))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return session_id
    except Exception as e:
        print(f"Error creating session: {e}")
        return None

def get_session(session_id: str) -> Optional[Dict]:
    """Get session data from database if valid and not expired"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, expires_at FROM sessions 
            WHERE session_id = %s AND expires_at > NOW()
        ''', (session_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return {
                'user_id': result[0],
                'username': result[1]
            }
        return None
    except Exception as e:
        print(f"Error getting session: {e}")
        return None

def delete_session(session_id: str) -> bool:
    """Delete a session from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM sessions WHERE session_id = %s', (session_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error deleting session: {e}")
        return False

def cleanup_expired_sessions():
    """Remove expired sessions from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM sessions WHERE expires_at <= NOW()')
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error cleaning up sessions: {e}")
        return False

def get_authenticated_user(request: Request) -> Optional[Dict]:
    """Get authenticated user from database session"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    
    # Use database session only
    return get_session(session_id)

# Initialize intelligent memory system globally
intelligent_memory_system = None
try:
    from intelligent_memory import IntelligentMemorySystem
    from background_riai import process_riai_batch, start_background_riai, stop_background_riai
    from tool_generator import ToolGenerator
    from tool_executor import ToolExecutor
    intelligent_memory_system = IntelligentMemorySystem()
    tool_generator = ToolGenerator()
    tool_executor = ToolExecutor()
    print("✅ Intelligent memory system initialized")
    print("✅ Tool generation system initialized")
except Exception as e:
    print(f"❌ Failed to initialize intelligent memory: {e}")
    intelligent_memory_system = None

# Memory summarizer removed - replaced by RIAI quality-boosted retrieval

# FastAPI event handlers for background service
@app.on_event("startup")
async def startup_event():
    """Initialize background services"""
    if intelligent_memory_system is not None:
        try:
            asyncio.create_task(start_background_riai())
            print("✅ Background RIAI service started")
        except Exception as e:
            print(f"❌ Failed to start background RIAI service: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background services"""
    if intelligent_memory_system is not None:
        try:
            await stop_background_riai()
            print("✅ Background RIAI service stopped")
        except Exception as e:
            print(f"❌ Failed to stop background RIAI service: {e}")

# Note: Sessions cleared on restart - users need to re-login

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def init_file_storage():
    """Initialize all database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                first_name VARCHAR(255) NOT NULL,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                title VARCHAR(255) NOT NULL,
                topic VARCHAR(255),
                sub_topic VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Create conversation messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id SERIAL PRIMARY KEY,
                conversation_id VARCHAR(255) NOT NULL,
                message_type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        ''')
        
        # Create user files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_files (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                file_type VARCHAR(50),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Create memory links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_links (
                id SERIAL PRIMARY KEY,
                source_memory_id VARCHAR(255) NOT NULL,
                linked_topic VARCHAR(255) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Create sessions table for persistent authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Create user_tools table for custom tool storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tools (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                tool_name VARCHAR(255) NOT NULL,
                function_code TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, tool_name)
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ All database tables initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Tool management functions
def store_user_tool(user_id: str, tool_name: str, function_code: str, schema_json: str, description: Optional[str] = None) -> bool:
    """Store a custom tool for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_tools (user_id, tool_name, function_code, schema_json, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, tool_name) 
            DO UPDATE SET 
                function_code = EXCLUDED.function_code,
                schema_json = EXCLUDED.schema_json,
                description = EXCLUDED.description,
                created_at = CURRENT_TIMESTAMP
        ''', (user_id, tool_name, function_code, schema_json, description or ""))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error storing user tool: {e}")
        return False

def get_user_tools(user_id: str) -> List[Dict]:
    """Get all active tools for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tool_name, function_code, schema_json, description, usage_count, success_count
            FROM user_tools
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
        ''', (user_id,))
        
        tools = []
        for row in cursor.fetchall():
            tools.append({
                'tool_name': row[0],
                'function_code': row[1],
                'schema_json': row[2],
                'description': row[3],
                'usage_count': row[4],
                'success_count': row[5]
            })
        
        cursor.close()
        conn.close()
        return tools
    except Exception as e:
        print(f"Error getting user tools: {e}")
        return []

def update_tool_usage(user_id: str, tool_name: str, success: bool = True) -> bool:
    """Update tool usage statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if success:
            cursor.execute('''
                UPDATE user_tools 
                SET usage_count = usage_count + 1, success_count = success_count + 1
                WHERE user_id = %s AND tool_name = %s
            ''', (user_id, tool_name))
        else:
            cursor.execute('''
                UPDATE user_tools 
                SET usage_count = usage_count + 1
                WHERE user_id = %s AND tool_name = %s
            ''', (user_id, tool_name))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating tool usage: {e}")
        return False

# Initialize file storage on startup
init_file_storage()



# Conversation database helper functions
def create_conversation(user_id: str, title: Optional[str] = None, topic: Optional[str] = None, sub_topic: Optional[str] = None) -> Optional[str]:
    """Create a new conversation and return its ID"""
    try:
        # Clean up any placeholder conversations for this topic/subtopic before creating real one
        cleanup_placeholder_conversations(user_id, topic, sub_topic)
        
        conversation_id = str(uuid.uuid4())
        if not title:
            title = "New Conversation"
        if not topic:
            topic = "general"
        
        # Normalize topic and sub_topic to lowercase
        topic = topic.lower().strip() if topic else "general"
        sub_topic = sub_topic.lower().strip() if sub_topic else None
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversations (id, user_id, title, topic, sub_topic, created_at, updated_at, message_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (conversation_id, user_id, title, topic, sub_topic, datetime.now(), datetime.now(), 0))
        conn.commit()
        cursor.close()
        conn.close()
        return conversation_id
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return None

def update_conversation_topic(conversation_id: str, topic: Optional[str] = None, sub_topic: Optional[str] = None) -> bool:
    """Update the topic and sub-topic of an existing conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE conversations 
            SET topic = %s, sub_topic = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (topic, sub_topic, conversation_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()
        return success
    except Exception as e:
        print(f"Error updating conversation topic: {e}")
        return False

def get_user_conversations(user_id: str, limit: int = 20, offset: int = 0, topic: Optional[str] = None, sub_topic: Optional[str] = None) -> Dict:
    """Get paginated conversations for a user with previews, optionally filtered by topic/subtopic"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause for filtering
        where_conditions = ['c.user_id = %s']
        params = [user_id]
        
        if topic is not None:
            # Normalize topic for consistent filtering
            topic = topic.lower().strip()
            where_conditions.append('c.topic = %s')
            params.append(topic)
            
        if sub_topic is not None:
            # Normalize sub_topic for consistent filtering
            sub_topic = sub_topic.lower().strip()
            where_conditions.append('c.sub_topic = %s')
            params.append(sub_topic)
        
        where_clause = ' AND '.join(where_conditions)
        
        # Get total count with filtering
        count_query = f'SELECT COUNT(*) FROM conversations c WHERE {where_clause}'
        cursor.execute(count_query, params)
        count_result = cursor.fetchone()
        total_count = count_result[0] if count_result and count_result[0] is not None else 0
        
        # Get paginated conversations with latest message preview and filtering
        main_query = f'''
            SELECT c.id, c.title, c.topic, c.sub_topic, c.created_at, c.updated_at, c.message_count,
                   m.content as last_message, m.message_type as last_message_type
            FROM conversations c
            LEFT JOIN LATERAL (
                SELECT content, message_type 
                FROM conversation_messages 
                WHERE conversation_id = c.id 
                ORDER BY created_at DESC 
                LIMIT 1
            ) m ON true
            WHERE {where_clause}
            ORDER BY c.updated_at DESC
            LIMIT %s OFFSET %s
        '''
        
        cursor.execute(main_query, params + [limit, offset])
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                'id': row[0],
                'title': row[1],
                'topic': row[2],
                'sub_topic': row[3],
                'created_at': row[4].isoformat(),
                'updated_at': row[5].isoformat(),
                'message_count': row[6],
                'last_message': row[7],
                'last_message_type': row[8]
            })
        
        cursor.close()
        conn.close()
        
        return {
            'conversations': conversations,
            'total_count': total_count,
            'has_more': offset + limit < total_count,
            'next_offset': offset + limit if offset + limit < total_count else None
        }
    except Exception as e:
        print(f"Error getting conversations: {e}")
        return {'conversations': [], 'total_count': 0, 'has_more': False, 'next_offset': None}

def save_conversation_message(conversation_id: str, message_type: str, content: str):
    """Save a message to a conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert message and return the generated ID
        cursor.execute('''
            INSERT INTO conversation_messages (conversation_id, message_type, content, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (conversation_id, message_type, content, datetime.now()))
        
        result = cursor.fetchone()
        if not result:
            raise Exception("Failed to insert message")
        message_id = result[0]
        
        # Update conversation message count and timestamp
        cursor.execute('''
            UPDATE conversations 
            SET message_count = message_count + 1, updated_at = %s
            WHERE id = %s
        ''', (datetime.now(), conversation_id))
        
        # Update conversation title if it's the first user message
        if message_type == 'user':
            cursor.execute('SELECT message_count FROM conversations WHERE id = %s', (conversation_id,))
            count_result = cursor.fetchone()
            if count_result and count_result[0] is not None and count_result[0] == 1:  # First message, update title
                title = content[:50] + "..." if len(content) > 50 else content
                cursor.execute('UPDATE conversations SET title = %s WHERE id = %s', (title, conversation_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return message_id
    except Exception as e:
        print(f"Error saving message: {e}")
        return None

def get_conversation_messages(conversation_id: str, limit: int = 30, before_id: Optional[str] = None) -> Dict:
    """Get paginated messages for a conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total message count
        cursor.execute('SELECT COUNT(*) FROM conversation_messages WHERE conversation_id = %s', (conversation_id,))
        count_result = cursor.fetchone()
        total_count = count_result[0] if count_result and count_result[0] is not None else 0
        
        if before_id:
            # Load messages before a specific message ID
            cursor.execute('''
                SELECT m1.id, m1.message_type, m1.content, m1.created_at
                FROM conversation_messages m1
                JOIN conversation_messages m2 ON m2.id = %s AND m2.conversation_id = %s
                WHERE m1.conversation_id = %s AND m1.created_at < m2.created_at
                ORDER BY m1.created_at DESC
                LIMIT %s
            ''', (before_id, conversation_id, conversation_id, limit))
            
            # Reverse to get chronological order
            rows = list(reversed(cursor.fetchall()))
        else:
            # Load most recent messages
            cursor.execute('''
                SELECT id, message_type, content, created_at
                FROM conversation_messages
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            ''', (conversation_id, limit))
            
            # Reverse to get chronological order
            rows = list(reversed(cursor.fetchall()))
        
        messages = []
        for row in rows:
            messages.append({
                'id': str(row[0]),
                'message_type': row[1],
                'content': row[2],
                'created_at': row[3].isoformat()
            })
        
        cursor.close()
        conn.close()
        
        # Check if there are more messages before the oldest returned message
        has_more = False
        if messages:
            oldest_id = messages[0]['id']
            cursor = get_db_connection().cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM conversation_messages 
                WHERE conversation_id = %s AND created_at < (
                    SELECT created_at FROM conversation_messages WHERE id = %s
                )
            ''', (conversation_id, oldest_id))
            more_result = cursor.fetchone()
            has_more = more_result[0] > 0 if more_result and more_result[0] is not None else False
            cursor.close()
        
        return {
            'messages': messages,
            'total_count': total_count,
            'has_more': has_more,
            'oldest_id': str(messages[0]['id']) if messages else None
        }
    except Exception as e:
        print(f"Error getting messages: {e}")
        return {'messages': [], 'total_count': 0, 'has_more': False, 'oldest_id': None}

def get_conversation_messages_all(conversation_id: str) -> List[Dict]:
    """Get all messages for a conversation (legacy function for backward compatibility)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, message_type, content, created_at
            FROM conversation_messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        ''', (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': str(row[0]),
                'message_type': row[1],
                'content': row[2],
                'created_at': row[3].isoformat()
            })
        
        cursor.close()
        conn.close()
        return messages
    except Exception as e:
        print(f"Error getting messages: {e}")
        return []

# Topic management functions
def get_all_topics(user_id: str) -> Dict:
    """Get all topics and sub-topics for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT topic, sub_topic
            FROM conversations
            WHERE user_id = %s AND topic IS NOT NULL
            ORDER BY topic, sub_topic
        ''', (user_id,))
        
        topics = {}
        for row in cursor.fetchall():
            topic = row[0]
            sub_topic = row[1]
            if topic not in topics:
                topics[topic] = []
            if sub_topic and sub_topic not in topics[topic]:
                topics[topic].append(sub_topic)
        
        cursor.close()
        conn.close()
        return topics
    except Exception as e:
        print(f"Error getting topics: {e}")
        return {}

def get_sub_topic_count(user_id: str, topic: str) -> int:
    """Get count of sub-topics for a topic"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(DISTINCT sub_topic)
            FROM conversations
            WHERE user_id = %s AND topic = %s AND sub_topic IS NOT NULL
        ''', (user_id, topic.lower()))
        
        count_result = cursor.fetchone()
        count = count_result[0] if count_result and count_result[0] is not None else 0
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f"Error getting sub-topic count: {e}")
        return 0

def create_topic_entry(user_id: str, topic: str) -> bool:
    """Create a topic entry without a conversation"""
    try:
        topic = topic.lower().strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if topic already exists
        cursor.execute('''
            SELECT COUNT(*) FROM conversations 
            WHERE user_id = %s AND topic = %s
        ''', (user_id, topic))
        
        exists_result = cursor.fetchone()
        if exists_result and exists_result[0] is not None and exists_result[0] > 0:
            cursor.close()
            conn.close()
            return True  # Topic already exists
        
        # Create a placeholder conversation for the topic
        conversation_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO conversations (id, user_id, title, topic, created_at, updated_at, message_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (conversation_id, user_id, f"[Topic: {topic}]", topic, datetime.now(), datetime.now(), 0))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating topic: {e}")
        return False

def create_subtopic_entry(user_id: str, topic: str, sub_topic: str) -> bool:
    """Create a sub-topic entry under an existing topic"""
    try:
        topic = topic.lower().strip()
        sub_topic = sub_topic.lower().strip()
        
        # Check sub-topic limit
        if get_sub_topic_count(user_id, topic) >= 5:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if sub-topic already exists
        cursor.execute('''
            SELECT COUNT(*) FROM conversations 
            WHERE user_id = %s AND topic = %s AND sub_topic = %s
        ''', (user_id, topic, sub_topic))
        
        subtopic_exists_result = cursor.fetchone()
        if subtopic_exists_result and subtopic_exists_result[0] is not None and subtopic_exists_result[0] > 0:
            cursor.close()
            conn.close()
            return True  # Sub-topic already exists
        
        # Create a placeholder conversation for the sub-topic
        conversation_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO conversations (id, user_id, title, topic, sub_topic, created_at, updated_at, message_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (conversation_id, user_id, f"[Sub-topic: {topic} → {sub_topic}]", topic, sub_topic, datetime.now(), datetime.now(), 0))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating sub-topic: {e}")
        return False

def cleanup_placeholder_conversations(user_id: str, topic: Optional[str], sub_topic: Optional[str]) -> int:
    """Remove placeholder conversations that match the topic/subtopic being used for real conversation"""
    try:
        if not topic:
            return 0  # No cleanup needed if no topic specified
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Normalize topic and sub_topic like the rest of the system
        topic = topic.lower().strip()
        sub_topic = sub_topic.lower().strip() if sub_topic else None
        
        # Find placeholder conversations that match exactly
        # Placeholders have 0 messages and specific title patterns
        if sub_topic:
            # Looking for subtopic placeholder: [Sub-topic: topic → sub_topic]
            placeholder_title = f"[Sub-topic: {topic} → {sub_topic}]"
            cursor.execute('''
                SELECT id FROM conversations 
                WHERE user_id = %s AND topic = %s AND sub_topic = %s 
                AND message_count = 0 AND title = %s
            ''', (user_id, topic, sub_topic, placeholder_title))
        else:
            # Looking for topic placeholder: [Topic: topic]
            placeholder_title = f"[Topic: {topic}]"
            cursor.execute('''
                SELECT id FROM conversations 
                WHERE user_id = %s AND topic = %s AND sub_topic IS NULL 
                AND message_count = 0 AND title = %s
            ''', (user_id, topic, placeholder_title))
        
        placeholder_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete the placeholder conversations
        deleted_count = 0
        for placeholder_id in placeholder_ids:
            cursor.execute('DELETE FROM conversations WHERE id = %s', (placeholder_id,))
            deleted_count += cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted_count > 0:
            print(f"DEBUG: Cleaned up {deleted_count} placeholder conversation(s) for topic '{topic}'" + 
                  (f" → '{sub_topic}'" if sub_topic else ""))
        
        return deleted_count
        
    except Exception as e:
        print(f"Error cleaning up placeholder conversations: {e}")
        return 0

# Memory linking functions
def create_memory_link(memory_id: str, linked_topic: str, user_id: str) -> bool:
    """Create a link between a memory and a topic"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if link already exists
        cursor.execute('''
            SELECT COUNT(*) FROM memory_links 
            WHERE source_memory_id = %s AND linked_topic = %s AND user_id = %s
        ''', (memory_id, linked_topic.lower(), user_id))
        
        link_exists_result = cursor.fetchone()
        if link_exists_result and link_exists_result[0] is not None and link_exists_result[0] > 0:
            cursor.close()
            conn.close()
            return True  # Link already exists
        
        # Create new link
        cursor.execute('''
            INSERT INTO memory_links (source_memory_id, linked_topic, user_id, created_at)
            VALUES (%s, %s, %s, %s)
        ''', (memory_id, linked_topic.lower(), user_id, datetime.now()))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating memory link: {e}")
        return False

def remove_topic_links(current_topic: str, linked_topic: str, user_id: str) -> bool:
    """Remove all links between current topic and linked topic"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Remove links where memories from current_topic are linked to linked_topic
        cursor.execute('''
            DELETE FROM memory_links 
            WHERE linked_topic = %s AND user_id = %s
            AND source_memory_id IN (
                SELECT DISTINCT m.id FROM conversations c
                JOIN messages msg ON c.id = msg.conversation_id
                JOIN neo4j_memories m ON m.user_id = %s
                WHERE c.topic = %s
            )
        ''', (linked_topic.lower(), user_id, user_id, current_topic.lower()))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error removing topic links: {e}")
        return False

def get_linked_memories(current_topic: str, user_id: str, limit: int = 2) -> List[str]:
    """Get memory IDs that are linked to other topics from the current topic"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT ml.source_memory_id, ml.linked_topic
            FROM memory_links ml
            WHERE ml.user_id = %s
            ORDER BY ml.created_at DESC
            LIMIT %s
        ''', (user_id, limit))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [row[0] for row in results]
    except Exception as e:
        print(f"Error getting linked memories: {e}")
        return []

# Topic deletion functions
def get_topic_deletion_info(user_id: str, topic: str) -> Dict:
    """Get information about what will be deleted when deleting a topic"""
    try:
        topic = topic.lower().strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get conversation count and subtopics
        cursor.execute('''
            SELECT COUNT(*) as conversation_count,
                   COUNT(DISTINCT sub_topic) as subtopic_count,
                   COALESCE(SUM(message_count), 0) as total_messages
            FROM conversations
            WHERE user_id = %s AND topic = %s
        ''', (user_id, topic))
        
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return {'exists': False}
        
        conversation_count = result[0] if result[0] is not None else 0
        subtopic_count = result[1] if result[1] is not None and result[1] > 0 else 0
        total_messages = result[2] if result[2] is not None else 0
        
        # Get list of subtopics
        cursor.execute('''
            SELECT DISTINCT sub_topic
            FROM conversations
            WHERE user_id = %s AND topic = %s AND sub_topic IS NOT NULL
        ''', (user_id, topic))
        
        subtopics = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            'topic': topic,
            'conversation_count': conversation_count,
            'subtopic_count': subtopic_count,
            'subtopics': subtopics,
            'total_messages': total_messages,
            'exists': conversation_count > 0
        }
    except Exception as e:
        print(f"Error getting topic deletion info: {e}")
        return {'exists': False}

def get_subtopic_deletion_info(user_id: str, topic: str, subtopic: str) -> Dict:
    """Get information about what will be deleted when deleting a subtopic"""
    try:
        topic = topic.lower().strip()
        subtopic = subtopic.lower().strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get conversation count and message count for this subtopic
        cursor.execute('''
            SELECT COUNT(*) as conversation_count,
                   COALESCE(SUM(message_count), 0) as total_messages
            FROM conversations
            WHERE user_id = %s AND topic = %s AND sub_topic = %s
        ''', (user_id, topic, subtopic))
        
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return {'exists': False}
        
        conversation_count = result[0] if result[0] is not None else 0
        total_messages = result[1] if result[1] is not None else 0
        
        cursor.close()
        conn.close()
        
        return {
            'topic': topic,
            'subtopic': subtopic,
            'conversation_count': conversation_count,
            'total_messages': total_messages,
            'exists': conversation_count > 0
        }
    except Exception as e:
        print(f"Error getting subtopic deletion info: {e}")
        return {'exists': False}

def delete_topic_and_data(user_id: str, topic: str) -> bool:
    """Delete a topic and all associated data from both PostgreSQL and Neo4j"""
    try:
        topic = topic.lower().strip()
        
        # First get all conversation IDs for this topic
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM conversations
            WHERE user_id = %s AND topic = %s
        ''', (user_id, topic))
        
        conversation_ids = [row[0] for row in cursor.fetchall()]
        
        if not conversation_ids:
            cursor.close()
            conn.close()
            return False  # Topic doesn't exist
        
        # Begin transaction
        conn.autocommit = False
        
        try:
            # Delete from PostgreSQL in proper order
            # 1. Delete memory links
            cursor.execute('''
                DELETE FROM memory_links
                WHERE user_id = %s AND linked_topic = %s
            ''', (user_id, topic))
            
            # 2. Delete conversation messages
            for conv_id in conversation_ids:
                cursor.execute('''
                    DELETE FROM conversation_messages
                    WHERE conversation_id = %s
                ''', (conv_id,))
            
            # 3. Delete conversations
            cursor.execute('''
                DELETE FROM conversations
                WHERE user_id = %s AND topic = %s
            ''', (user_id, topic))
            
            # Commit PostgreSQL transaction
            conn.commit()
            
            # Delete from Neo4j - memories associated with these conversations
            from intelligent_memory import IntelligentMemorySystem
            memory_system = IntelligentMemorySystem()
            
            with memory_system.driver.session() as session:
                for conv_id in conversation_ids:
                    session.run("""
                        MATCH (m:IntelligentMemory {user_id: $user_id, conversation_id: $conversation_id})
                        DELETE m
                    """, {'user_id': user_id, 'conversation_id': conv_id})
            
            memory_system.close()
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"Error during topic deletion transaction: {e}")
            return False
            
    except Exception as e:
        print(f"Error deleting topic: {e}")
        return False

def delete_subtopic_and_data(user_id: str, topic: str, subtopic: str) -> bool:
    """Delete a subtopic and all associated data from both PostgreSQL and Neo4j"""
    try:
        topic = topic.lower().strip()
        subtopic = subtopic.lower().strip()
        
        # First get all conversation IDs for this subtopic
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM conversations
            WHERE user_id = %s AND topic = %s AND sub_topic = %s
        ''', (user_id, topic, subtopic))
        
        conversation_ids = [row[0] for row in cursor.fetchall()]
        
        if not conversation_ids:
            cursor.close()
            conn.close()
            return False  # Subtopic doesn't exist
        
        # Begin transaction
        conn.autocommit = False
        
        try:
            # Delete from PostgreSQL in proper order
            # 1. Delete conversation messages
            for conv_id in conversation_ids:
                cursor.execute('''
                    DELETE FROM conversation_messages
                    WHERE conversation_id = %s
                ''', (conv_id,))
            
            # 2. Delete conversations
            cursor.execute('''
                DELETE FROM conversations
                WHERE user_id = %s AND topic = %s AND sub_topic = %s
            ''', (user_id, topic, subtopic))
            
            # Commit PostgreSQL transaction
            conn.commit()
            
            # Delete from Neo4j - memories associated with these conversations
            from intelligent_memory import IntelligentMemorySystem
            memory_system = IntelligentMemorySystem()
            
            with memory_system.driver.session() as session:
                for conv_id in conversation_ids:
                    session.run("""
                        MATCH (m:IntelligentMemory {user_id: $user_id, conversation_id: $conversation_id})
                        DELETE m
                    """, {'user_id': user_id, 'conversation_id': conv_id})
            
            memory_system.close()
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"Error during subtopic deletion transaction: {e}")
            return False
            
    except Exception as e:
        print(f"Error deleting subtopic: {e}")
        return False

# Chat models - define before usage
class ChatMessage(BaseModel):
    message: str
    model: Optional[str] = "gpt-4o-mini"
    conversation_id: Optional[str] = None
    web_search: Optional[bool] = False

class ChatResponse(BaseModel):
    response: str
    memory_stored: bool
    context_used: int
    conversation_id: str
    assistant_message_id: Optional[str] = None
    deletion_info: Optional[Dict] = None

# Slash command handler
async def handle_slash_command(command: str, user_id: str, conversation_id: str) -> ChatResponse:
    """Handle slash commands for file management"""
    parts = command.strip().split()
    cmd = parts[0].lower()
    
    try:
        if cmd == '/files':
            # List all files
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT filename, file_type, uploaded_at FROM user_files WHERE user_id = %s ORDER BY uploaded_at DESC", (user_id,))
            files = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not files:
                response = "No files uploaded yet. Use the + button to upload files."
            else:
                response = "**Your uploaded files:**\n\n"
                for filename, file_type, uploaded_at in files:
                    date = uploaded_at.strftime("%Y-%m-%d %H:%M")
                    response += f"• `{filename}` ({file_type}) - {date}\n"
                response += f"\nUse `/view [filename]` to display file content."
            
        elif cmd == '/view':
            if len(parts) < 2:
                response = "Usage: `/view [filename]`\nExample: `/view main.py`"
            else:
                filename = ' '.join(parts[1:])
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT content FROM user_files WHERE user_id = %s AND filename = %s", (user_id, filename))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if result:
                    response = f"**File: {filename}**\n\n```\n{result[0]}\n```"
                else:
                    response = f"File '{filename}' not found. Use `/files` to see available files."
        
        elif cmd == '/delete':
            if len(parts) < 2:
                response = "Usage: `/delete [filename]`\nExample: `/delete main.py`"
            else:
                filename = ' '.join(parts[1:])
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_files WHERE user_id = %s AND filename = %s", (user_id, filename))
                deleted = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
                
                if deleted > 0:
                    response = f"File '{filename}' deleted successfully."
                else:
                    response = f"File '{filename}' not found."
        
        elif cmd == '/search':
            if len(parts) < 2:
                response = "Usage: `/search [term]`\nExample: `/search main`"
            else:
                search_term = ' '.join(parts[1:])
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT filename, file_type, uploaded_at FROM user_files WHERE user_id = %s AND filename ILIKE %s ORDER BY uploaded_at DESC", (user_id, f"%{search_term}%"))
                files = cursor.fetchall()
                cursor.close()
                conn.close()
                
                if not files:
                    response = f"No files found matching '{search_term}'."
                else:
                    response = f"**Files matching '{search_term}':**\n\n"
                    for filename, file_type, uploaded_at in files:
                        date = uploaded_at.strftime("%Y-%m-%d %H:%M")
                        response += f"• `{filename}` ({file_type}) - {date}\n"
        
        elif cmd == '/download':
            if len(parts) < 2:
                response = "Usage: `/download [filename]`\nExample: `/download main.py`"
            else:
                filename = ' '.join(parts[1:])
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT filename FROM user_files WHERE user_id = %s AND filename = %s", (user_id, filename))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if result:
                    download_url = f"/api/download/{filename}"
                    response = f"**Download ready:** `{filename}`\n\nClick here to download: [Download {filename}]({download_url})\n\nOr visit: `{download_url}`"
                else:
                    response = f"File '{filename}' not found. Use `/files` to see available files."
        
        elif cmd == '/topics':
            # List all topics and sub-topics
            topics = get_all_topics(user_id)
            if not topics:
                response = "No topics created yet. Start a conversation with a topic to organize your chats."
            else:
                response = "**Your Topics:**\n\n"
                for topic, sub_topics in topics.items():
                    response += f"• **{topic}**\n"
                    if sub_topics:
                        for sub_topic in sub_topics:
                            response += f"  - {sub_topic}\n"
                    else:
                        response += f"  - (no sub-topics)\n"
                response += "\nUse topics when creating new conversations to organize your chats."
        
        elif cmd == '/link':
            if len(parts) < 2:
                response = "Usage: `/link [topic]`\nExample: `/link cooking`\nThis will link your next message to memories from the specified topic."
            else:
                linked_topic = ' '.join(parts[1:]).lower()
                
                # Get current conversation topic
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT topic FROM conversations WHERE id = %s', (conversation_id,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if not result:
                    response = "Error: Could not find current conversation."
                else:
                    current_topic = result[0]
                    response = f"Ready to link your next message to **{linked_topic}** topic. Your next message will be connected to memories from that topic."
                    
                    # Store the linking intent in session (we'll implement this in the chat handler)
                    # For now, just confirm the command
        
        elif cmd == '/unlink':
            if len(parts) < 2:
                response = "Usage: `/unlink [topic]`\nExample: `/unlink cooking`\nThis will remove all links between current topic and the specified topic."
            else:
                linked_topic = ' '.join(parts[1:]).lower()
                
                # Get current conversation topic
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT topic FROM conversations WHERE id = %s', (conversation_id,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if not result:
                    response = "Error: Could not find current conversation."
                else:
                    current_topic = result[0]
                    if current_topic:
                        success = remove_topic_links(current_topic, linked_topic, user_id)
                        if success:
                            response = f"Removed all links between **{current_topic}** and **{linked_topic}** topics."
                        else:
                            response = f"Error removing links between topics."
                    else:
                        response = "Current conversation has no topic set."
        
        elif cmd == '/delete-topic':
            if len(parts) < 2:
                response = "Usage: `/delete-topic [topic_name]`\nExample: `/delete-topic cooking`\n⚠️ **Warning:** This will delete the entire topic, all its subtopics, conversations, and memories permanently."
            else:
                topic_name = ' '.join(parts[1:]).lower()
                print(f"DEBUG: Processing delete-topic command for: {topic_name}")
                
                # Get deletion info first
                info = get_topic_deletion_info(user_id, topic_name)
                print(f"DEBUG: Topic deletion info: {info}")
                
                if not info['exists']:
                    response = f"Topic '{topic_name}' not found. Use `/topics` to see available topics."
                else:
                    # Return JSON for frontend popup
                    print("DEBUG: Returning DELETION_CONFIRM response")
                    return ChatResponse(
                        response="DELETION_CONFIRM",
                        memory_stored=False,
                        context_used=0,
                        conversation_id=conversation_id,
                        deletion_info={
                            "type": "topic",
                            "topic": info['topic'],
                            "subtopic": None,
                            "conversation_count": info['conversation_count'],
                            "subtopic_count": info['subtopic_count'],
                            "subtopics": info['subtopics'],
                            "total_messages": info['total_messages']
                        }
                    )
        
        elif cmd == '/delete-subtopic':
            if len(parts) < 3:
                response = "Usage: `/delete-subtopic [topic] [subtopic]`\nExample: `/delete-subtopic cooking recipes`\n⚠️ **Warning:** This will delete the subtopic and all its conversations and memories permanently."
            else:
                topic_name = parts[1].lower()
                subtopic_name = ' '.join(parts[2:]).lower()
                
                # Get deletion info first
                info = get_subtopic_deletion_info(user_id, topic_name, subtopic_name)
                
                if not info['exists']:
                    response = f"Subtopic '{subtopic_name}' under topic '{topic_name}' not found. Use `/topics` to see available topics and subtopics."
                else:
                    # Return JSON for frontend popup
                    return ChatResponse(
                        response="DELETION_CONFIRM",
                        memory_stored=False,
                        context_used=0,
                        conversation_id=conversation_id,
                        deletion_info={
                            "type": "subtopic",
                            "topic": info['topic'],
                            "subtopic": info['subtopic'],
                            "conversation_count": info['conversation_count'],
                            "subtopic_count": 0,
                            "subtopics": [],
                            "total_messages": info['total_messages']
                        }
                    )
        

        
        else:
            response = "**Available commands:**\n\n• `/files` - List all uploaded files\n• `/view [filename]` - Display file content\n• `/delete [filename]` - Delete a file\n• `/search [term]` - Search files by name\n• `/download [filename]` - Download a file\n• `/topics` - List all topics and sub-topics\n• `/link [topic]` - Link current message to specified topic\n• `/unlink [topic]` - Remove links between topics\n• `/delete-topic [topic]` - Delete a topic and all its data\n• `/delete-subtopic [topic] [subtopic]` - Delete a subtopic and all its data"
        
        # Save command and response to conversation
        save_conversation_message(conversation_id, 'user', command)
        save_conversation_message(conversation_id, 'assistant', response)
        
        return ChatResponse(
            response=response,
            memory_stored=False,
            context_used=0,
            conversation_id=conversation_id
        )
        
    except Exception as e:
        return ChatResponse(
            response=f"Error processing command: {str(e)}",
            memory_stored=False,
            context_used=0,
            conversation_id=conversation_id
        )

def hash_password(password: str) -> str:
    """Hash password using BCrypt with salt"""
    return pwd_context.hash(password)

def create_user_in_db(first_name: str, username: str, email: str, password_hash: str) -> bool:
    """Create user in both PostgreSQL and Neo4j databases"""
    user_id = str(uuid.uuid4())
    
    try:
        # First, check if user exists in PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False  # User already exists
        
        # Create user in PostgreSQL
        cursor.execute(
            "INSERT INTO users (id, first_name, username, email, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (user_id, first_name, username, email, password_hash)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        # Neo4j user creation removed - handled by intelligent_memory when needed
        
        return True
        
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def verify_user_login(username: str, password: str) -> Optional[str]:
    """Verify user login with BCrypt and migrate from SHA256 if needed"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, password_hash FROM users WHERE username = %s",
            (username,)
        )
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return None
        
        user_id, stored_hash = result
        
        # Check if this is a BCrypt hash (starts with $2b$)
        if stored_hash.startswith('$2b$'):
            # Use BCrypt verification
            if pwd_context.verify(password, stored_hash):
                cursor.close()
                conn.close()
                return user_id
        else:
            # Legacy SHA256 hash - verify and migrate if successful
            legacy_hash = hashlib.sha256(password.encode()).hexdigest()
            if legacy_hash == stored_hash:
                # Password is correct, migrate to BCrypt
                new_hash = pwd_context.hash(password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (new_hash, user_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                print(f"Migrated user {username} to BCrypt")
                return user_id
        
        cursor.close()
        conn.close()
        return None
    except Exception as e:
        print(f"Error verifying login: {e}")
        return None

def get_user_first_name(user_id: str) -> Optional[str]:
    """Get user's first name by user ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT first_name FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting user first name: {e}")
        return None

# Registration and login pages
@app.get("/register")
async def register_page():
    """Serve registration page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NeuroLM - Register</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #000000;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow-y: auto;
                padding: 1rem 0;
            }
            
            .background-pattern {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: url('/static/neural-brain-logo.png');
                background-size: 40%;
                background-position: center;
                background-repeat: no-repeat;
                opacity: 0.05;
                filter: blur(1px);
                z-index: 0;
            }
            
            .register-container {
                background: rgba(26, 26, 26, 0.95);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 20px;
                padding: 2.5rem;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
                width: 100%;
                max-width: 420px;
                position: relative;
                z-index: 1;
                transition: all 0.3s ease;
            }
            .logo {
                text-align: center;
                margin-bottom: 2rem;
            }
            .logo h1 {
                background: linear-gradient(135deg, 
                    #667eea 0%, 
                    #764ba2 25%, 
                    #667eea 50%, 
                    #a855f7 75%, 
                    #667eea 100%);
                background-size: 200% 200%;
                background-clip: text;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin: 0;
                font-size: 2rem;
                font-weight: 700;
                animation: iridescent 3s ease-in-out infinite;
                filter: drop-shadow(0 0 10px rgba(102, 126, 234, 0.3));
                text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
            }
            .logo p {
                color: #ffffff !important;
                font-size: 1.2rem;
                font-weight: 500;
                margin-top: 0.5rem;
                margin-bottom: 0;
            }
            
            @keyframes iridescent {
                0%, 100% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #e5e7eb;
                font-weight: 500;
            }
            input[type="text"], input[type="email"], input[type="password"] {
                width: 100%;
                padding: 0.875rem 1rem;
                background: rgba(42, 42, 42, 0.8);
                border: 1px solid #404040;
                border-radius: 12px;
                font-size: 1rem;
                color: #ffffff;
                transition: all 0.3s ease;
                box-sizing: border-box;
            }
            input[type="text"]:focus, input[type="email"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                background: rgba(42, 42, 42, 1);
            }
            .submit-btn {
                width: 100%;
                padding: 0.75rem;
                background: linear-gradient(135deg, 
                    rgba(102, 126, 234, 0.3) 0%, 
                    rgba(118, 75, 162, 0.3) 50%, 
                    rgba(168, 85, 247, 0.3) 100%);
                backdrop-filter: blur(10px);
                border: 2px solid transparent;
                border-radius: 12px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                color: white;
                position: relative;
                overflow: hidden;
                transition: all 0.3s ease;
                box-shadow: 
                    0 4px 15px rgba(102, 126, 234, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
            
            .submit-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, 
                    transparent, 
                    rgba(255, 255, 255, 0.3), 
                    transparent);
                transition: left 0.6s;
            }
            
            .submit-btn:hover::before {
                left: 100%;
            }
            
            .submit-btn:hover {
                transform: translateY(-2px);
                box-shadow: 
                    0 6px 20px rgba(102, 126, 234, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
                border-color: rgba(102, 126, 234, 0.5);
            }
            .submit-btn:hover {
                background: #3a5a95;
            }
            .login-link {
                text-align: center;
                margin-top: 1.5rem;
            }
            .login-link p {
                color: #e5e7eb;
                font-size: 0.9rem;
            }
            .login-link a {
                color: #667eea;
                text-decoration: none;
            }
            .error {
                color: #e74c3c;
                font-size: 0.9rem;
                margin-top: 0.5rem;
            }
        </style>
    </head>
    <body>
        <div class="register-container">
            <div class="logo">
                <img src="/static/neurolm-glass-logo.png" alt="NeuroLM" style="max-width: 240px; height: auto; filter: brightness(1.1) contrast(1.05);">
                <p>Create Your Account</p>
            </div>
            <form action="/register" method="post" onsubmit="return validateForm()">
                <div class="form-group">
                    <label for="first_name">First Name / Preferred Name:</label>
                    <input type="text" id="first_name" name="first_name" required>
                </div>
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <div class="form-group">
                    <label for="confirm_password">Confirm Password:</label>
                    <input type="password" id="confirm_password" name="confirm_password" required>
                    <div id="password-error" class="error" style="display: none;">Passwords do not match</div>
                </div>
                <button type="submit" class="submit-btn">Create Account</button>
            </form>
            <div class="login-link">
                <p>Already have an account? <a href="/login">Sign in here</a></p>
            </div>
        </div>
        
        <script>
            function validateForm() {
                const password = document.getElementById('password').value;
                const confirmPassword = document.getElementById('confirm_password').value;
                const errorDiv = document.getElementById('password-error');
                
                if (password !== confirmPassword) {
                    errorDiv.style.display = 'block';
                    return false;
                }
                errorDiv.style.display = 'none';
                return true;
            }
        </script>
    </body>
    </html>
    """)

@app.post("/register")
async def register_user(
    first_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Handle user registration"""
    # Validate passwords match
    if password != confirm_password:
        return HTMLResponse("""
        <script>
            alert('Passwords do not match');
            window.location.href = '/register';
        </script>
        """)
    
    # Hash password and create user
    password_hash = hash_password(password)
    success = create_user_in_db(first_name, username, email, password_hash)
    
    if not success:
        return HTMLResponse("""
        <script>
            alert('Username or email already exists. Please choose different credentials.');
            window.location.href = '/register';
        </script>
        """)
    
    # Redirect to login page
    return HTMLResponse("""
    <script>
        alert('Account created successfully! Please log in.');
        window.location.href = '/login';
    </script>
    """)

@app.get("/login")
async def login_page():
    """Serve login page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NeuroLM - Login</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #000000;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow-y: auto;
                padding: 1rem 0;
            }
            
            /* Subtle brain pattern background */
            .background-pattern {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image: url('/static/neural-brain-logo.png');
                background-size: 40%;
                background-position: center;
                background-repeat: no-repeat;
                opacity: 0.05;
                filter: blur(1px);
                z-index: 0;
            }
            
            /* Floating login card */
            .login-container {
                background: linear-gradient(135deg, 
                    rgba(26, 26, 26, 0.85) 0%, 
                    rgba(40, 40, 40, 0.85) 50%, 
                    rgba(26, 26, 26, 0.85) 100%);
                backdrop-filter: blur(20px);
                border: 2px solid;
                border-image: linear-gradient(135deg, 
                    rgba(102, 126, 234, 0.6) 0%, 
                    rgba(118, 75, 162, 0.6) 25%, 
                    rgba(168, 85, 247, 0.6) 50%, 
                    rgba(102, 126, 234, 0.6) 100%) 1;
                border-radius: 20px;
                padding: 2.5rem;
                box-shadow: 
                    0 20px 40px rgba(0, 0, 0, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1),
                    0 0 0 1px rgba(102, 126, 234, 0.3);
                width: 100%;
                max-width: 420px;
                position: relative;
                z-index: 1;
                transition: all 0.3s ease;
            }
            
            .login-container:hover {
                border-color: rgba(102, 126, 234, 0.5);
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.6);
            }
            
            .logo {
                text-align: center;
                margin-bottom: 2.5rem;
            }
            
            .logo h1 {
                background: linear-gradient(135deg, 
                    #667eea 0%, 
                    #764ba2 25%, 
                    #667eea 50%, 
                    #a855f7 75%, 
                    #667eea 100%);
                background-size: 200% 200%;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin: 0;
                font-size: 2.5rem;
                font-weight: 700;
                letter-spacing: -0.025em;
                animation: iridescent 3s ease-in-out infinite;
                filter: drop-shadow(0 0 10px rgba(102, 126, 234, 0.3));
                text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
            }
            
            @keyframes iridescent {
                0%, 100% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
            }
            
            .logo p {
                color: #9ca3af;
                margin-top: 0.5rem;
                font-size: 1rem;
            }
            
            .form-group {
                margin-bottom: 1.5rem;
            }
            
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #e5e7eb;
                font-weight: 500;
                font-size: 0.9rem;
            }
            
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 0.875rem 1rem;
                background: rgba(42, 42, 42, 0.8);
                border: 1px solid #404040;
                border-radius: 12px;
                font-size: 1rem;
                color: #ffffff;
                transition: all 0.3s ease;
                box-sizing: border-box;
            }
            
            input[type="text"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                background: rgba(42, 42, 42, 1);
            }
            
            input[type="text"]::placeholder, input[type="password"]::placeholder {
                color: #6b7280;
            }
            
            .remember-me {
                display: flex;
                align-items: center;
                margin-bottom: 1.5rem;
                gap: 0.5rem;
            }
            
            .remember-me input[type="checkbox"] {
                width: auto;
                margin: 0;
                accent-color: #667eea;
            }
            
            .remember-me label {
                margin: 0;
                font-size: 0.875rem;
                color: #9ca3af;
                cursor: pointer;
            }
            
            .submit-btn {
                width: 100%;
                padding: 1rem 2rem;
                background: linear-gradient(135deg, 
                    rgba(20, 30, 60, 0.4) 0%, 
                    rgba(40, 50, 100, 0.3) 50%, 
                    rgba(20, 30, 60, 0.4) 100%);
                backdrop-filter: blur(20px);
                border: 2px solid transparent;
                border-radius: 50px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                color: #ffffff;
                position: relative;
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 
                    0 0 0 1px rgba(0, 255, 255, 0.3),
                    0 0 0 2px rgba(138, 43, 226, 0.2),
                    0 0 0 3px rgba(0, 255, 127, 0.1),
                    0 4px 20px rgba(0, 255, 255, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2),
                    inset 0 -1px 0 rgba(255, 255, 255, 0.1);
                background-clip: padding-box;
            }
            
            .submit-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(90deg, 
                    rgba(0, 255, 255, 0.6) 0%,
                    rgba(138, 43, 226, 0.6) 25%,
                    rgba(0, 255, 127, 0.6) 50%,
                    rgba(0, 191, 255, 0.6) 75%,
                    rgba(0, 255, 255, 0.6) 100%);
                background-size: 300% 300%;
                border-radius: 50px;
                padding: 2px;
                mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
                mask-composite: exclude;
                -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
                -webkit-mask-composite: source-out;
                animation: iridescent-border 3s linear infinite;
                z-index: -1;
            }
            
            .submit-btn::after {
                content: '';
                position: absolute;
                top: 20%;
                left: 10%;
                right: 10%;
                height: 1px;
                background: linear-gradient(90deg, 
                    transparent, 
                    rgba(255, 255, 255, 0.4), 
                    transparent);
                border-radius: 1px;
                z-index: 1;
            }
            
            @keyframes iridescent-border {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            
            .submit-btn:hover {
                transform: translateY(-1px) scale(1.02);
                box-shadow: 
                    0 0 0 1px rgba(0, 255, 255, 0.5),
                    0 0 0 2px rgba(138, 43, 226, 0.4),
                    0 0 0 3px rgba(0, 255, 127, 0.3),
                    0 6px 30px rgba(0, 255, 255, 0.3),
                    0 0 40px rgba(138, 43, 226, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3),
                    inset 0 -1px 0 rgba(255, 255, 255, 0.2);
            }
            
            .submit-btn:active {
                transform: translateY(0) scale(1);
            }
            
            .register-link {
                text-align: center;
                margin-top: 2rem;
                padding-top: 1.5rem;
                border-top: 1px solid rgba(64, 64, 64, 0.5);
            }
            
            .register-link p {
                color: #9ca3af;
                font-size: 0.9rem;
            }
            
            .register-link a {
                color: #667eea;
                text-decoration: none;
                font-weight: 500;
                transition: color 0.3s ease;
            }
            
            .register-link a:hover {
                color: #764ba2;
            }
            
            /* Mobile responsiveness */
            @media (max-width: 480px) {
                .login-container {
                    margin: 1rem;
                    padding: 2rem;
                }
                
                .logo h1 {
                    font-size: 2rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="background-pattern"></div>
        <div class="login-container">
            <div class="logo">
                <img src="/static/neurolm-glass-logo.png" alt="NeuroLM" style="max-width: 240px; height: auto; filter: brightness(1.1) contrast(1.05);">
                <p>Sign in to your account</p>
            </div>
            <form action="/login" method="post">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" placeholder="Enter your username" required>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" placeholder="Enter your password" required>
                </div>
                <div class="remember-me">
                    <input type="checkbox" id="remember_me" name="remember_me">
                    <label for="remember_me">Keep me signed in for 30 days</label>
                </div>
                <button type="submit" class="submit-btn">Sign In</button>
            </form>
            <div class="register-link">
                <p>Don't have an account? <a href="/register">Create one here</a></p>
            </div>
        </div>
    </body>
    </html>
    """)

@app.post("/login")
async def login_user(
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False)
):
    """Handle user login"""
    user_id = verify_user_login(username, password)
    
    if not user_id:
        return HTMLResponse("""
        <script>
            alert('Invalid username or password');
            window.location.href = '/login';
        </script>
        """)
    
    # Create session in database with extended duration if remember me is checked
    session_id = create_session(user_id, username, extended=remember_me)
    
    if not session_id:
        return HTMLResponse("""
        <script>
            alert('Failed to create session. Please try again.');
            window.location.href = '/login';
        </script>
        """)
    
    # Redirect to chat with session
    response = RedirectResponse(url="/", status_code=302)
    
    # Set cookie with extended max_age if remember me is checked
    if remember_me:
        # 30 days in seconds
        max_age = 30 * 24 * 60 * 60
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=max_age)
    else:
        # Session cookie (expires when browser closes)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
    
    return response

# Serve the chat interface as the main page
@app.get("/")
async def serve_chat(request: Request):
    """Serve the chat interface"""
    # Check if user is logged in
    user_data = get_authenticated_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
    
    return FileResponse("chat.html")

@app.get("/mobile")
async def serve_mobile(request: Request):
    """Serve the mobile PWA interface"""
    # Check if user is logged in
    user_data = get_authenticated_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
    
    return FileResponse("mobile.html")

@app.get("/manifest.json")
async def serve_manifest():
    """Serve PWA manifest"""
    return FileResponse("manifest.json")

@app.get("/sw.js")
async def serve_service_worker():
    """Serve service worker"""
    return FileResponse("sw.js")





# Conversation models
class ConversationCreate(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    sub_topic: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    topic: Optional[str]
    sub_topic: Optional[str]
    created_at: str
    updated_at: str
    message_count: int
    last_message: Optional[str] = None
    last_message_type: Optional[str] = None

class ConversationMessage(BaseModel):
    id: str
    message_type: str
    content: str
    created_at: str

class MessageListResponse(BaseModel):
    messages: List[ConversationMessage]
    total_count: int
    has_more: bool
    oldest_id: Optional[str]

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_memory(chat_request: ChatMessage, request: Request):
    """
    Chat with LLM using memory system for context
    """
    try:
        # Extract user_id from session
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        # Check for slash commands
        if chat_request.message.startswith('/'):
            conversation_id = chat_request.conversation_id or create_conversation(user_id)
            if conversation_id:
                return await handle_slash_command(chat_request.message, user_id, conversation_id)
            else:
                return ChatResponse(
                    response="Error creating conversation for command processing.",
                    memory_stored=False,
                    context_used=0,
                    conversation_id=""
                )
        
        # Check for /link command within message and extract it
        link_topic = None
        message_content = chat_request.message
        if message_content.startswith('/link '):
            parts = message_content.split(' ', 2)
            if len(parts) >= 3:
                link_topic = parts[1].lower()
                message_content = parts[2]  # Extract actual message content after /link [topic]
            elif len(parts) == 2:
                # Just /link [topic] without message content
                fallback_conversation_id = chat_request.conversation_id or create_conversation(user_id)
                return ChatResponse(
                    response=f"Please include your message after `/link {parts[1]}`. Example: `/link cooking I love pasta recipes`",
                    memory_stored=False,
                    context_used=0,
                    conversation_id=fallback_conversation_id or ""
                )
        
        # Handle conversation management first to ensure we have topic context
        conversation_id = chat_request.conversation_id
        if not conversation_id:
            # Create new conversation if none specified
            conversation_id = create_conversation(user_id)
        
        # Get current conversation topic context
        current_topic = None
        current_subtopic = None
        search_scope = "conversation"  # Default for new conversations
        
        if conversation_id:
            # Get conversation details to extract topic context
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT topic, sub_topic FROM conversations WHERE id = %s', (conversation_id,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if result:
                    current_topic = result[0]
                    current_subtopic = result[1]
                    search_scope = "topic" if current_topic else "conversation"
            except Exception as e:
                print(f"Error getting conversation topic: {e}")
        
        # Use intelligent memory system for fast, smart retrieval
        context = ""
        if intelligent_memory_system:
            try:
                context = await intelligent_memory_system.retrieve_memory(
                    query=chat_request.message,
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                print(f"DEBUG: Intelligent memory retrieved: {len(context)} chars")
                if context:
                    print(f"DEBUG: Memory context preview: {context[:200]}...")
            except Exception as e:
                print(f"Intelligent memory error (continuing without memory): {e}")
                context = ""
        
        # Check if user is asking about files and add file content to context
        file_query_keywords = ["file", "main.py", "analyze", "code", "script", "upload"]
        is_file_query = any(keyword in chat_request.message.lower() for keyword in file_query_keywords)
        
        if is_file_query:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT filename, content FROM user_files WHERE user_id = %s ORDER BY uploaded_at DESC LIMIT 5",
                    (user_id,)
                )
                user_files = cursor.fetchall()
                cursor.close()
                conn.close()
                
                if user_files:
                    context += "\n\nAvailable files:\n"
                    for filename, content in user_files:
                        context += f"\n--- {filename} ---\n{content}\n"
            except Exception as e:
                print(f"Error fetching user files: {e}")
        
        # Get user's first name for personalized responses
        user_first_name = get_user_first_name(user_id)
        
        # User message will be stored in memory after PostgreSQL save to get proper message_id
        
        # Generate response using LLM with memory context
        from model_service import ModelService
        model_service = ModelService()
        
        # Create system message with user context and memories
        system_content = f"""You are a helpful AI assistant with access to conversation history with {user_first_name or "the user"}.

IMPORTANT: The following are actual previous conversations and messages from your chat history with this user. These are REAL memories, not hypothetical:

{context if context else "No previous conversation history available."}

Instructions:
- Use the conversation history above to maintain continuity
- Reference specific details from previous conversations when relevant
- Be consistent with what you remember from past interactions
- If the user asks about previous conversations, refer to the actual content above
- Do not contradict information from your previous responses shown above"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": chat_request.message}
        ]
        
        try:
            response_text = await model_service.chat_completion(
                messages=messages,
                model=chat_request.model or "openai/gpt-4o-mini",
                web_search=chat_request.web_search or False
            )
            print(f"DEBUG: Generated response: {response_text[:100]}...")
        except Exception as e:
            print(f"LLM error: {e}")
            response_text = "I apologize, but I'm experiencing technical difficulties processing your request right now."
        
        # Assistant response will be stored in memory after PostgreSQL save to get proper message_id
        
        # Ensure conversation_id is not None before saving messages
        user_message_id = None
        assistant_message_id = None
        assistant_memory_node_id = None
        if conversation_id:
            try:
                # Save user message to conversation and get PostgreSQL message ID
                user_message_id = save_conversation_message(conversation_id, 'user', chat_request.message)
                
                # Save assistant response to conversation and get PostgreSQL message ID
                assistant_message_id = save_conversation_message(conversation_id, 'assistant', response_text)
                
                # Now store messages in intelligent memory system with PostgreSQL message IDs
                if intelligent_memory_system:
                    try:
                        # Store user message with PostgreSQL message ID
                        if user_message_id:
                            user_memory_id = await intelligent_memory_system.store_memory(
                                content=message_content,
                                user_id=user_id,
                                conversation_id=conversation_id,
                                message_type="user",
                                message_id=user_message_id
                            )
                            if user_memory_id:
                                print(f"DEBUG: Stored user message with PostgreSQL ID {user_message_id}")
                        
                        # Store assistant response with PostgreSQL message ID
                        if assistant_message_id:
                            assistant_memory_node_id = await intelligent_memory_system.store_memory(
                                content=response_text,
                                user_id=user_id,
                                conversation_id=conversation_id,
                                message_type="assistant",
                                message_id=assistant_message_id
                            )
                            if assistant_memory_node_id:
                                print(f"DEBUG: Stored assistant response with PostgreSQL ID {assistant_message_id}")
                                print(f"DEBUG: Memory {assistant_memory_node_id} queued for background R(t) evaluation")
                                
                    except Exception as e:
                        print(f"Error storing messages in intelligent memory: {e}")
                        
            except Exception as e:
                print(f"Error saving conversation messages: {e}")
        else:
            print("Warning: Could not create conversation, messages not saved")
        
        return ChatResponse(
            response=response_text,
            memory_stored=True,
            context_used=1 if context else 0,
            conversation_id=conversation_id or "",
            assistant_message_id=assistant_memory_node_id if assistant_memory_node_id else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Conversation management endpoints
class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total_count: int
    has_more: bool
    next_offset: Optional[int]

@app.get("/api/conversations", response_model=ConversationListResponse)
async def get_conversations(request: Request, limit: int = 20, offset: int = 0, topic: Optional[str] = None, sub_topic: Optional[str] = None):
    """Get paginated conversations for the current user, optionally filtered by topic/subtopic"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        result = get_user_conversations(user_id, limit, offset, topic, sub_topic)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Conversations error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting conversations: {str(e)}")

@app.post("/api/conversations/new", response_model=ConversationResponse)
async def create_new_conversation(request: Request, conversation_data: ConversationCreate):
    """Create a new conversation"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        # Validate sub-topic limit if provided
        if conversation_data.topic and conversation_data.sub_topic:
            sub_topic_count = get_sub_topic_count(user_id, conversation_data.topic)
            if sub_topic_count >= 5:
                raise HTTPException(status_code=400, detail=f"Maximum 5 sub-topics allowed per topic. Topic '{conversation_data.topic}' already has {sub_topic_count} sub-topics.")
        
        conversation_id = create_conversation(user_id, conversation_data.title, conversation_data.topic, conversation_data.sub_topic)
        if not conversation_id:
            raise HTTPException(status_code=500, detail="Failed to create conversation")
        
        # Get the created conversation details
        conversations_data = get_user_conversations(user_id, limit=20, offset=0, topic=None, sub_topic=None)
        new_conversation = next((c for c in conversations_data['conversations'] if c['id'] == conversation_id), None)
        
        if not new_conversation:
            raise HTTPException(status_code=500, detail="Created conversation not found")
        
        return new_conversation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.get("/api/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages_endpoint(conversation_id: str, request: Request, limit: int = 30, before_id: Optional[str] = None):
    """Get paginated messages for a specific conversation"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        result = get_conversation_messages(conversation_id, limit, before_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversation messages: {str(e)}")

@app.get("/api/conversations/{conversation_id}/messages/all", response_model=List[ConversationMessage])
async def get_conversation_messages_all_endpoint(conversation_id: str, request: Request):
    """Get all messages for a specific conversation (legacy endpoint)"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        messages = get_conversation_messages_all(conversation_id)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversation messages: {str(e)}")

@app.get("/api/topics")
async def get_topics_endpoint(request: Request):
    """Get all topics and sub-topics for the current user"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        topics = get_all_topics(user_id)
        return topics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting topics: {str(e)}")

@app.get("/api/user/name")
async def get_user_name_endpoint(request: Request):
    """Get the current user's first name"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        first_name = get_user_first_name(user_id)
        
        # Get user feedback score
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT feedback_score FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            feedback_score = result[0] if result else 0
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"ERROR: Failed to get user feedback score: {e}")
            feedback_score = 0
            cursor.close()
            conn.close()
        
        return {"first_name": first_name, "feedback_score": feedback_score}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user name: {str(e)}")

class TopicCreate(BaseModel):
    name: str

class SubtopicCreate(BaseModel):
    name: str

@app.post("/api/topics")
async def create_topic_endpoint(request: Request, topic_data: TopicCreate):
    """Create a new topic"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        if not topic_data.name or not topic_data.name.strip():
            raise HTTPException(status_code=400, detail="Topic name cannot be empty")
        
        success = create_topic_entry(user_id, topic_data.name)
        if success:
            return {"success": True, "topic": topic_data.name.lower().strip()}
        else:
            raise HTTPException(status_code=500, detail="Failed to create topic")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating topic: {str(e)}")

@app.post("/api/topics/{topic}/subtopics")
async def create_subtopic_endpoint(request: Request, topic: str, subtopic_data: SubtopicCreate):
    """Create a new sub-topic under an existing topic"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        if not subtopic_data.name or not subtopic_data.name.strip():
            raise HTTPException(status_code=400, detail="Sub-topic name cannot be empty")
        
        # Check if topic exists
        topics = get_all_topics(user_id)
        if topic.lower() not in topics:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Check sub-topic limit
        if get_sub_topic_count(user_id, topic) >= 5:
            raise HTTPException(status_code=400, detail="Maximum 5 sub-topics allowed per topic")
        
        success = create_subtopic_entry(user_id, topic, subtopic_data.name)
        if success:
            return {"success": True, "topic": topic.lower(), "sub_topic": subtopic_data.name.lower().strip()}
        else:
            raise HTTPException(status_code=500, detail="Failed to create sub-topic")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating sub-topic: {str(e)}")

class ConversationTopicUpdate(BaseModel):
    topic: Optional[str] = None
    sub_topic: Optional[str] = None

@app.put("/api/conversations/{conversation_id}/topic")
async def update_conversation_topic_endpoint(conversation_id: str, request: Request, topic_data: ConversationTopicUpdate):
    """Update the topic and sub-topic of an existing conversation"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        # Verify the conversation belongs to the user
        conversations = get_user_conversations(user_id, limit=1000, offset=0, topic=None, sub_topic=None)  # Get all conversations to check ownership
        conversation_exists = any(conv['id'] == conversation_id for conv in conversations['conversations'])
        
        if not conversation_exists:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update the conversation topic
        success = update_conversation_topic(conversation_id, topic_data.topic, topic_data.sub_topic)
        
        if success:
            return {"success": True, "conversation_id": conversation_id, "topic": topic_data.topic, "sub_topic": topic_data.sub_topic}
        else:
            raise HTTPException(status_code=500, detail="Failed to update conversation topic")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating conversation topic: {str(e)}")

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request):
    """Delete a conversation and all its memories"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        # Verify the conversation belongs to the user
        conversations = get_user_conversations(user_id, limit=1000, offset=0, topic=None, sub_topic=None)
        conversation_exists = any(conv['id'] == conversation_id for conv in conversations['conversations'])
        
        if not conversation_exists:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete from Neo4j intelligent memory system
        try:
            if intelligent_memory_system:
                with intelligent_memory_system.driver.session() as session:
                    result = session.run("""
                        MATCH (m:IntelligentMemory)
                        WHERE m.conversation_id = $conversation_id AND m.user_id = $user_id
                        DELETE m
                        RETURN count(*) as deleted_count
                    """, {
                        'conversation_id': conversation_id,
                        'user_id': user_id
                    })
                    memory_result = result.single()
                    deleted_memories = memory_result['deleted_count'] if memory_result else 0
                    print(f"Deleted {deleted_memories} memories from Neo4j")
        except Exception as e:
            print(f"Error deleting memories from Neo4j: {e}")
            # Continue with PostgreSQL deletion even if Neo4j fails
        
        # Delete from PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete conversation messages first (foreign key constraint)
        cursor.execute("DELETE FROM conversation_messages WHERE conversation_id = %s", (conversation_id,))
        
        # Delete the conversation
        cursor.execute("DELETE FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"success": True, "message": "Conversation and memories deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")


# Clear database endpoint
@app.post("/api/clear-memory")
async def clear_memory_database():
    """Clear all data from Neo4j database"""
    try:
        from intelligent_memory import intelligent_memory
        with intelligent_memory.driver.session() as session:
            # Delete all nodes and relationships
            session.run("MATCH (n) DETACH DELETE n")
            
        return {"status": "success", "message": "All memory data cleared from database"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")

# File upload endpoint
@app.post("/api/upload-file")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload and store file content in PostgreSQL"""
    try:
        # Get user from session
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Store in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_files (user_id, filename, content, file_type) VALUES (%s, %s, %s, %s)",
            (user_id, file.filename, file_content, file.content_type)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"message": f"File {file.filename} uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Download file endpoint
@app.get("/api/download/{filename}")
async def download_file(filename: str, request: Request):
    """Download a file for the current user"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content, file_type FROM user_files WHERE user_id = %s AND filename = %s",
            (user_id, filename)
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        
        content, file_type = result
        
        # Set appropriate headers for file download
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": file_type or "application/octet-stream"
        }
        
        return Response(content=content, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

# Get user files endpoint
@app.get("/api/user-files")
async def get_user_files(request: Request, search: Optional[str] = None):
    """Get all files for the current user with optional search"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if search is not None:
            cursor.execute("""
                SELECT id, filename, file_type, uploaded_at, 
                       LEFT(content, 100) as content_preview
                FROM user_files 
                WHERE user_id = %s AND filename ILIKE %s
                ORDER BY uploaded_at DESC
            """, (user_id, f"%{search}%"))
        else:
            cursor.execute("""
                SELECT id, filename, file_type, uploaded_at,
                       LEFT(content, 100) as content_preview
                FROM user_files 
                WHERE user_id = %s
                ORDER BY uploaded_at DESC
            """, (user_id,))
        
        files = []
        for row in cursor.fetchall():
            files.append({
                'id': row[0],
                'filename': row[1],
                'file_type': row[2],
                'uploaded_at': row[3].isoformat(),
                'content_preview': row[4] + "..." if len(row[4]) == 100 else row[4]
            })
        
        cursor.close()
        conn.close()
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting files: {str(e)}")

# Get all available models from OpenRouter
@app.get("/api/models")
async def get_available_models():
    """Get all available models from OpenRouter"""
    try:
        from model_service import ModelService
        model_service = ModelService()
        models = model_service.get_models()
        # Sort alphabetically by name
        models.sort(key=lambda x: x.get('name', '').lower())
        return models
    except Exception as e:
        # Return basic models if OpenRouter is unavailable
        default_models = [
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "description": "Fast and efficient model for general chat"},
            {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash", "description": "Google's latest fast model"}
        ]
        return default_models

@app.delete("/api/topics/{topic_name}")
async def delete_topic_endpoint(topic_name: str, request: Request):
    """Delete a topic and all its data"""
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    success = delete_topic_and_data(user_id, topic_name.lower())
    
    if success:
        return {"success": True, "message": f"Topic '{topic_name}' has been permanently deleted."}
    else:
        raise HTTPException(status_code=400, detail=f"Error deleting topic '{topic_name}'. The topic may not exist or there was a system error.")

@app.delete("/api/topics/{topic_name}/subtopics/{subtopic_name}")
async def delete_subtopic_endpoint(topic_name: str, subtopic_name: str, request: Request):
    """Delete a subtopic and all its data"""
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    success = delete_subtopic_and_data(user_id, topic_name.lower(), subtopic_name.lower())
    
    if success:
        return {"success": True, "message": f"Subtopic '{subtopic_name}' has been permanently deleted from topic '{topic_name}'."}
    else:
        raise HTTPException(status_code=400, detail=f"Error deleting subtopic '{subtopic_name}' from topic '{topic_name}'. It may not exist or there was a system error.")

# Daily summary endpoint removed - functionality replaced by RIAI quality-boosted retrieval

# RIAI test endpoint
@app.post("/api/test-riai")
async def test_riai_scoring(request: Request):
    """Test RIAI background scoring system"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        if not intelligent_memory_system:
            raise HTTPException(status_code=500, detail="RIAI system not available")
        
        # Run background R(t) evaluation
        result = await process_riai_batch()
        
        return {
            "status": "success",
            "riai_results": result,
            "message": f"Background R(t) evaluation: {result.get('processed', 0)} processed, {result.get('cached', 0)} cached, {result.get('evaluated', 0)} evaluated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RIAI test failed: {str(e)}")

# Human feedback endpoint for RIAI H(t) function
class FeedbackRequest(BaseModel):
    message_id: str
    feedback_type: str  # 'great_response', 'that_worked', 'not_helpful' (legacy: 'like', 'dislike')

@app.post("/api/feedback")
async def submit_feedback(feedback_request: FeedbackRequest, request: Request):
    """Submit human feedback for RIAI H(t) function"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        # Validate feedback type
        valid_feedback_types = ['great_response', 'that_worked', 'not_helpful', 'like', 'dislike']
        if feedback_request.feedback_type not in valid_feedback_types:
            raise HTTPException(status_code=400, detail=f"Invalid feedback type. Must be one of: {valid_feedback_types}")
        
        if not intelligent_memory_system:
            raise HTTPException(status_code=500, detail="Memory system not available")
        
        # Convert feedback to H(t) score using new differential scoring system
        feedback_scores = {
            'not_helpful': -3.0,      # Severe negative feedback
            'like': 1.5,              # Legacy positive feedback  
            'great_response': 1.5,    # Good response
            'that_worked': 2.5,       # Highest score for practical success
            'dislike': -3.0           # Legacy negative feedback
        }
        feedback_score = feedback_scores[feedback_request.feedback_type]
        
        # Update memory with human feedback using Neo4j node ID directly
        print(f"DEBUG: Feedback endpoint called with message_id={feedback_request.message_id}, type={feedback_request.feedback_type}, user_id={user_id}")
        success = await intelligent_memory_system.update_human_feedback_by_node_id(
            node_id=feedback_request.message_id,
            feedback_score=feedback_score,
            feedback_type=feedback_request.feedback_type,
            user_id=user_id
        )
        
        if success:
            # Calculate final quality score using f(R(t), H(t))
            await intelligent_memory_system.update_final_quality_score(
                memory_id=feedback_request.message_id,
                user_id=user_id,
                use_message_id=False  # Now using Neo4j node ID directly
            )
            
            # Increment user feedback score by 1 (only if not already awarded for this message)
            if intelligent_memory_system:
                try:
                    # Check if UF Score already awarded for this Neo4j node
                    with intelligent_memory_system.driver.session() as session:
                        result = session.run("""
                            MATCH (m:IntelligentMemory {id: $node_id, user_id: $user_id})
                            RETURN m.uf_score_awarded AS awarded
                        """, {
                            'node_id': feedback_request.message_id,
                            'user_id': user_id
                        })
                        
                        record = result.single()
                        if record and not record['awarded']:
                            # Award the UF Score point
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE users SET feedback_score = feedback_score + 1 WHERE id = %s",
                                (user_id,)
                            )
                            conn.commit()
                            cursor.close()
                            conn.close()
                            
                            # Mark this Neo4j node as having awarded UF Score
                            session.run("""
                                MATCH (m:IntelligentMemory {id: $node_id, user_id: $user_id})
                                SET m.uf_score_awarded = true
                            """, {
                                'node_id': feedback_request.message_id,
                                'user_id': user_id
                            })
                            
                            print(f"DEBUG: UF Score awarded for node {feedback_request.message_id}")
                        else:
                            print(f"DEBUG: UF Score already awarded for node {feedback_request.message_id}, skipping increment")
                            
                except Exception as e:
                    print(f"ERROR: Failed to update user feedback score: {e}")
                    # Don't fail the entire request for score update issues
            
            return {
                "status": "success",
                "message": f"Feedback recorded: {feedback_request.feedback_type}",
                "h_t_score": feedback_score
            }
        else:
            raise HTTPException(status_code=404, detail="Message not found or feedback update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")

# Implicit feedback endpoint for behavioral signals
class ImplicitFeedbackRequest(BaseModel):
    message_id: str
    action_type: str  # 'copy', 'continue', etc.
    feedback_score: float  # Implicit score value

@app.post("/api/feedback-implicit")
async def submit_implicit_feedback(feedback_request: ImplicitFeedbackRequest, request: Request):
    """Submit implicit behavioral feedback for RIAI H(t) function"""
    try:
        user_data = get_authenticated_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_data['user_id']
        
        # Validate action type and score
        valid_actions = ['copy', 'continue', 'followup']
        if feedback_request.action_type not in valid_actions:
            raise HTTPException(status_code=400, detail=f"Invalid action type. Must be one of: {valid_actions}")
        
        if not -1.0 <= feedback_request.feedback_score <= 1.0:
            raise HTTPException(status_code=400, detail="Feedback score must be between -1.0 and 1.0")
        
        if not intelligent_memory_system:
            raise HTTPException(status_code=500, detail="Memory system not available")
        
        # Update memory with implicit feedback
        success = await intelligent_memory_system.update_human_feedback(
            message_id=feedback_request.message_id,
            feedback_score=feedback_request.feedback_score,
            feedback_type=f"implicit_{feedback_request.action_type}",
            user_id=user_id
        )
        
        if success:
            # Calculate final quality score using f(R(t), H(t))
            await intelligent_memory_system.update_final_quality_score(
                memory_id=feedback_request.message_id,
                user_id=user_id,
                use_message_id=True
            )
            
            return {
                "status": "success",
                "message": f"Implicit feedback recorded: {feedback_request.action_type}",
                "h_t_score": feedback_request.feedback_score
            }
        else:
            # Don't fail silently for implicit feedback - just log and continue
            return {
                "status": "skipped",
                "message": "Message not found or already has feedback"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        # Implicit feedback failures should not break user experience
        return {
            "status": "error",
            "message": "Implicit feedback failed silently"
        }

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {"status": "healthy", "service": "NeuroLM Memory System"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)