from fastapi import FastAPI, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from memory_api import *
from pydantic import BaseModel
import uvicorn
import os
import httpx
import hashlib
import uuid
import psycopg2
from typing import Optional, List, Dict
from datetime import datetime

# Create FastAPI application
app = FastAPI(title="NeuroLM Memory System", version="1.0.0")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-here")

# Include memory API routes
app.include_router(router, prefix="/api")

# Mount static files for PWA
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global session storage (in production, use Redis or database)
user_sessions = {}
memory_system = MemorySystem()

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
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ All database tables initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Initialize file storage on startup
init_file_storage()

# Conversation database helper functions
def create_conversation(user_id: str, title: Optional[str] = None, topic: Optional[str] = None, sub_topic: Optional[str] = None) -> Optional[str]:
    """Create a new conversation and return its ID"""
    try:
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

def get_user_conversations(user_id: str, limit: int = 20, offset: int = 0) -> Dict:
    """Get paginated conversations for a user with previews"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM conversations WHERE user_id = %s', (user_id,))
        total_count = cursor.fetchone()[0]
        
        # Get paginated conversations with latest message preview
        cursor.execute('''
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
            WHERE c.user_id = %s
            ORDER BY c.updated_at DESC
            LIMIT %s OFFSET %s
        ''', (user_id, limit, offset))
        
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
        
        # Insert message
        cursor.execute('''
            INSERT INTO conversation_messages (conversation_id, message_type, content, created_at)
            VALUES (%s, %s, %s, %s)
        ''', (conversation_id, message_type, content, datetime.now()))
        
        # Update conversation message count and timestamp
        cursor.execute('''
            UPDATE conversations 
            SET message_count = message_count + 1, updated_at = %s
            WHERE id = %s
        ''', (datetime.now(), conversation_id))
        
        # Update conversation title if it's the first user message
        if message_type == 'user':
            cursor.execute('SELECT message_count FROM conversations WHERE id = %s', (conversation_id,))
            count = cursor.fetchone()[0]
            if count == 1:  # First message, update title
                title = content[:50] + "..." if len(content) > 50 else content
                cursor.execute('UPDATE conversations SET title = %s WHERE id = %s', (title, conversation_id))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error saving message: {e}")

def get_conversation_messages(conversation_id: str, limit: int = 30, before_id: str = None) -> Dict:
    """Get paginated messages for a conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total message count
        cursor.execute('SELECT COUNT(*) FROM conversation_messages WHERE conversation_id = %s', (conversation_id,))
        total_count = cursor.fetchone()[0]
        
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
            has_more = cursor.fetchone()[0] > 0
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
        
        count = cursor.fetchone()[0]
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
        
        if cursor.fetchone()[0] > 0:
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
        
        if cursor.fetchone()[0] > 0:
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
        
        if cursor.fetchone()[0] > 0:
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

# Chat models - define before usage
class ChatMessage(BaseModel):
    message: str
    model: Optional[str] = "gpt-4o-mini"
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    memory_stored: bool
    context_used: int
    conversation_id: str

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
        
        else:
            response = "**Available commands:**\n\n• `/files` - List all uploaded files\n• `/view [filename]` - Display file content\n• `/delete [filename]` - Delete a file\n• `/search [term]` - Search files by name\n• `/download [filename]` - Download a file\n• `/topics` - List all topics and sub-topics\n• `/link [topic]` - Link current message to specified topic\n• `/unlink [topic]` - Remove links between topics"
        
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
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

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
        
        # Create user in Neo4j
        try:
            with memory_system.driver.session() as session:
                session.run(
                    "CREATE (u:User {id: $id, first_name: $first_name, username: $username, email: $email, password_hash: $password_hash, created_at: datetime()})",
                    id=user_id,
                    first_name=first_name,
                    username=username,
                    email=email,
                    password_hash=password_hash
                )
        except Exception as neo4j_error:
            print(f"Neo4j user creation failed (non-critical): {neo4j_error}")
        
        return True
        
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def verify_user_login(username: str, password: str) -> Optional[str]:
    """Verify user login and return user ID if successful"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute(
            "SELECT id FROM users WHERE username = %s AND password_hash = %s",
            (username, password_hash)
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
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
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
            }
            .register-container {
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
            }
            .logo {
                text-align: center;
                margin-bottom: 2rem;
            }
            .logo h1 {
                color: #4a6fa5;
                margin: 0;
                font-size: 2rem;
                font-weight: 700;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #333;
                font-weight: 500;
            }
            input[type="text"], input[type="email"], input[type="password"] {
                width: 100%;
                padding: 0.75rem;
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            input[type="text"]:focus, input[type="email"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: #4a6fa5;
            }
            .submit-btn {
                width: 100%;
                padding: 0.75rem;
                background: #4a6fa5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }
            .submit-btn:hover {
                background: #3a5a95;
            }
            .login-link {
                text-align: center;
                margin-top: 1.5rem;
            }
            .login-link a {
                color: #4a6fa5;
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
                <h1>NeuroLM</h1>
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
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
            }
            .login-container {
                background: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
            }
            .logo {
                text-align: center;
                margin-bottom: 2rem;
            }
            .logo h1 {
                color: #4a6fa5;
                margin: 0;
                font-size: 2rem;
                font-weight: 700;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #333;
                font-weight: 500;
            }
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 0.75rem;
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            input[type="text"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: #4a6fa5;
            }
            .submit-btn {
                width: 100%;
                padding: 0.75rem;
                background: #4a6fa5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }
            .submit-btn:hover {
                background: #3a5a95;
            }
            .register-link {
                text-align: center;
                margin-top: 1.5rem;
            }
            .register-link a {
                color: #4a6fa5;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <h1>NeuroLM</h1>
                <p>Sign in to your account</p>
            </div>
            <form action="/login" method="post">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
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
    password: str = Form(...)
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
    
    # Create session
    session_id = str(uuid.uuid4())
    user_sessions[session_id] = {
        'user_id': user_id,
        'username': username
    }
    
    # Redirect to chat with session
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="session_id", value=session_id, httponly=True)
    return response

# Serve the chat interface as the main page
@app.get("/")
async def serve_chat(request: Request):
    """Serve the chat interface"""
    # Check if user is logged in
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in user_sessions:
        return RedirectResponse(url="/login")
    
    return FileResponse("chat.html")

@app.get("/mobile")
async def serve_mobile(request: Request):
    """Serve the mobile PWA interface"""
    # Check if user is logged in
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in user_sessions:
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
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
        # Check for slash commands
        if chat_request.message.startswith('/'):
            return await handle_slash_command(chat_request.message, user_id, chat_request.conversation_id or create_conversation(user_id))
        
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
                return ChatResponse(
                    response=f"Please include your message after `/link {parts[1]}`. Example: `/link cooking I love pasta recipes`",
                    memory_stored=False,
                    context_used=0,
                    conversation_id=chat_request.conversation_id or create_conversation(user_id)
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
        try:
            from intelligent_memory import intelligent_memory
            context = await intelligent_memory.retrieve_memory(
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
        
        # Store user message using intelligent memory system
        user_memory_id = None
        try:
            user_memory_id = await intelligent_memory.store_memory(
                content=message_content,
                user_id=user_id,
                conversation_id=conversation_id,
                message_type="user"
            )
            if user_memory_id:
                print(f"DEBUG: Stored user message with ID: {user_memory_id}")
        except Exception as e:
            print(f"Error storing user message in intelligent memory: {e}")
        
        # Always ensure we have the user's name
        if not user_first_name:
            user_first_name = "User"
        
        print(f"DEBUG: User name: '{user_first_name}', Context length: {len(context)} chars")
        
        # Generate response that always uses the user's name and memory
        user_message_lower = chat_request.message.lower()
        
        # Create response that directly incorporates memory
        if any(word in user_message_lower for word in ['hello', 'hi', 'hey']):
            response_text = f"Hello {user_first_name}! "
            if context:
                response_text += "I remember our previous conversations. "
                if 'testing' in context.lower():
                    response_text += "You've been testing the memory system. "
                if 'memory' in context.lower():
                    response_text += "We've discussed memory functionality. "
            else:
                response_text += "Great to meet you! "
            response_text += "How can I help you today?"
            
        elif 'name' in user_message_lower:
            response_text = f"Your name is {user_first_name}."
            if context and 'name' in context.lower():
                response_text += " I have this stored from our previous conversations."
                
        elif any(word in user_message_lower for word in ['remember', 'recall', 'memory', 'conversations']):
            response_text = f"Yes {user_first_name}, "
            if context and len(context) > 20:
                # Extract specific details from memory
                context_snippets = [line.strip('- ') for line in context.split('\n')[:3] if line.strip()]
                if context_snippets:
                    response_text += f"I can recall our conversations. For example: {context_snippets[0][:150]}..."
                else:
                    response_text += "I have access to our conversation history but it's not retrieving properly right now."
            else:
                response_text += "the memory system should be working but I'm not seeing previous context."
                
        else:
            # For other queries, force the LLM to use the name and context
            from model_service import ModelService
            model_service = ModelService()
            
            enforced_prompt = f"""You MUST start your response with "Hi {user_first_name}!" or "{user_first_name},"

Retrieved conversation history:
{context}

Respond to: {chat_request.message}

Remember to use the user's name and reference relevant history."""

            try:
                response_text = await model_service.chat_completion(
                    messages=[{"role": "user", "content": enforced_prompt}],
                    model=chat_request.model or "openai/gpt-4o-mini"
                )
                
                # Force name injection if LLM ignored it
                if user_first_name not in response_text:
                    response_text = f"{user_first_name}, " + response_text
                    
            except Exception as e:
                print(f"LLM error: {e}")
                response_text = f"{user_first_name}, I understand your message but I'm having technical difficulties right now."
        
        # Store assistant response using intelligent memory system
        try:
            assistant_memory_id = await intelligent_memory.store_memory(
                content=response_text,
                user_id=user_id,
                conversation_id=conversation_id,
                message_type="assistant"
            )
            if assistant_memory_id:
                print(f"DEBUG: Stored assistant response with ID: {assistant_memory_id}")
        except Exception as e:
            print(f"Error storing assistant response in intelligent memory: {e}")
        
        # Ensure conversation_id is not None before saving messages
        if conversation_id:
            try:
                # Save user message to conversation
                save_conversation_message(conversation_id, 'user', chat_request.message)
                
                # Save assistant response to conversation
                save_conversation_message(conversation_id, 'assistant', response_text)
            except Exception as e:
                print(f"Error saving conversation messages: {e}")
        else:
            print("Warning: Could not create conversation, messages not saved")
        
        return ChatResponse(
            response=response_text,
            memory_stored=True,
            context_used=1 if context else 0,
            conversation_id=conversation_id or ""
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
async def get_conversations(request: Request, limit: int = 20, offset: int = 0):
    """Get paginated conversations for the current user"""
    try:
        session_id = request.cookies.get("session_id")
        print(f"Session ID: {session_id}, Available sessions: {len(user_sessions)}")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
        result = get_user_conversations(user_id, limit, offset)
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
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
        # Validate sub-topic limit if provided
        if conversation_data.topic and conversation_data.sub_topic:
            sub_topic_count = get_sub_topic_count(user_id, conversation_data.topic)
            if sub_topic_count >= 5:
                raise HTTPException(status_code=400, detail=f"Maximum 5 sub-topics allowed per topic. Topic '{conversation_data.topic}' already has {sub_topic_count} sub-topics.")
        
        conversation_id = create_conversation(user_id, conversation_data.title, conversation_data.topic, conversation_data.sub_topic)
        if not conversation_id:
            raise HTTPException(status_code=500, detail="Failed to create conversation")
        
        # Get the created conversation details
        conversations_data = get_user_conversations(user_id)
        new_conversation = next((c for c in conversations_data['conversations'] if c['id'] == conversation_id), None)
        
        if not new_conversation:
            raise HTTPException(status_code=500, detail="Created conversation not found")
        
        return new_conversation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.get("/api/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages_endpoint(conversation_id: str, request: Request, limit: int = 30, before_id: str = None):
    """Get paginated messages for a specific conversation"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        result = get_conversation_messages(conversation_id, limit, before_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversation messages: {str(e)}")

@app.get("/api/conversations/{conversation_id}/messages/all", response_model=List[ConversationMessage])
async def get_conversation_messages_all_endpoint(conversation_id: str, request: Request):
    """Get all messages for a specific conversation (legacy endpoint)"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        messages = get_conversation_messages_all(conversation_id)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversation messages: {str(e)}")

@app.get("/api/topics")
async def get_topics_endpoint(request: Request):
    """Get all topics and sub-topics for the current user"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
        topics = get_all_topics(user_id)
        return topics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting topics: {str(e)}")

@app.get("/api/user/name")
async def get_user_name_endpoint(request: Request):
    """Get the current user's first name"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
        first_name = get_user_first_name(user_id)
        return {"first_name": first_name}
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
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
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
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
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
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
        # Verify the conversation belongs to the user
        conversations = get_user_conversations(user_id, limit=1000, offset=0)  # Get all conversations to check ownership
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

# Clear database endpoint
@app.post("/api/clear-memory")
async def clear_memory_database():
    """Clear all data from Neo4j database"""
    try:
        memory_system = MemorySystem()
        with memory_system.driver.session() as session:
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
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
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
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
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
async def get_user_files(request: Request, search: str = None):
    """Get all files for the current user with optional search"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in user_sessions:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = user_sessions[session_id]['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if search:
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

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {"status": "healthy", "service": "NeuroLM Memory System"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)