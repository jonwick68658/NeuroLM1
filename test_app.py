import streamlit as st
import openai
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import hashlib
from datetime import datetime
import pytz

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
openai_client = openai.OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Simple embedding function using hash-based approach
def generate_embedding(text):
    """Generate simple hash-based embedding for text"""
    if not text or not text.strip():
        return [0.0] * 384
    
    # Create a simple hash-based embedding (384 dimensions)
    text_hash = hashlib.md5(text.encode()).hexdigest()
    embedding = []
    
    # Generate 384 float values from the hash
    for i in range(0, 384):
        hash_part = text_hash[(i % len(text_hash))]
        embedding.append(float(int(hash_part, 16)) / 15.0)
        
    return embedding

# Neo4j Memory System
class Neo4jMemory:
    def __init__(self):
        """Initialize Neo4j connection"""
        try:
            self.driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI"),
                auth=(os.getenv("NEO4J_USER"), 
                     os.getenv("NEO4J_PASSWORD"))
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            self._init_db()
            
        except Exception as e:
            raise Exception(f"Neo4j connection failed: {str(e)}")
    
    def _init_db(self):
        """Initialize database constraints and indexes"""
        with self.driver.session() as session:
            try:
                # Create constraints
                session.run("""
                CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE
                """)
                
                session.run("""
                CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE
                """)
                
                # Create vector index for embeddings
                session.run("""
                CREATE VECTOR INDEX memory_embeddings IF NOT EXISTS
                FOR (m:Memory) ON m.embedding
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 384,
                    `vector.similarity_function`: 'cosine'
                }}
                """)
                
            except Exception as e:
                # Continue even if constraints already exist
                pass
    
    def store_chat(self, user_id, role, content):
        """Store chat message with vector embedding"""
        try:
            embedding = generate_embedding(content)
            timestamp = datetime.now(pytz.utc).isoformat()
            
            with self.driver.session() as session:
                session.run("""
                MERGE (u:User {id: $user_id})
                WITH u
                CREATE (m:Memory {
                    id: randomUUID(),
                    role: $role,
                    type: 'chat',
                    content: $content,
                    timestamp: datetime($timestamp),
                    embedding: $embedding
                })
                CREATE (u)-[:CREATED]->(m)
                """, 
                user_id=user_id, 
                role=role, 
                content=content,
                timestamp=timestamp,
                embedding=embedding
                )
                
        except Exception as e:
            raise Exception(f"Chat storage failed: {str(e)}")
    
    def get_relevant_memories(self, query, user_id, limit=5):
        """Retrieve relevant memories using vector similarity search"""
        try:
            query_embedding = generate_embedding(query)
            
            with self.driver.session() as session:
                results = session.run("""
                CALL db.index.vector.queryNodes('memory_embeddings', $limit, $query_embedding) 
                YIELD node, score
                MATCH (node)<-[:CREATED]-(:User {id: $user_id})
                WHERE score > 0.3
                RETURN node.content AS content, score
                ORDER BY score DESC
                """, 
                query_embedding=query_embedding,
                user_id=user_id,
                limit=limit
                )
                
                memories = [record["content"] for record in results]
                return memories
                
        except Exception as e:
            return []
    
    def get_memory_count(self, user_id):
        """Get total number of memories for a user"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                MATCH (u:User {id: $user_id})-[:CREATED]->(m:Memory)
                RETURN count(m) AS count
                """, user_id=user_id)
                
                record = result.single()
                return record["count"] if record else 0
                
        except Exception as e:
            return 0

# Initialize memory system
@st.cache_resource
def init_memory():
    try:
        return Neo4jMemory()
    except Exception as e:
        st.sidebar.warning(f"Neo4j connection issue: {str(e)}")
        return None

memory = init_memory()
DEFAULT_USER = "default_user"

# This line was moved to fix the Streamlit configuration error

# Custom CSS for sleek interface
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%);
        color: white;
    }
    .stSidebar {
        background: linear-gradient(180deg, #111827 0%, #1f2937 100%);
    }
</style>
""", unsafe_allow_html=True)

# Simple login check
def check_login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        with st.sidebar:
            st.markdown("### 🔐 Second Brain Access")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("🧠 Access Brain"):
                app_user = os.getenv("APP_USERNAME")
                app_pass = os.getenv("APP_PASSWORD")
                
                if not app_user or not app_pass:
                    st.error("App credentials not configured")
                    return False
                
                if username == app_user and password == app_pass:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        return False
    return True

# Main interface
def main():
    if check_login():
        st.title("🧠 Second Brain AI")
        st.write("Welcome to your AI assistant!")
        
        with st.sidebar:
            st.markdown("### 🎛️ Brain Controls")
            st.markdown("---")
            
            if st.button("🚪 Logout"):
                st.session_state.authenticated = False
                st.rerun()
            
            # Advanced Memory Stats
            if memory:
                try:
                    stats = memory.get_memory_stats(DEFAULT_USER)
                    st.metric("🧠 Total Memories", stats["total_memories"])
                    st.metric("💪 Strong Memories", stats["strong_memories"])
                    st.metric("📊 Avg Confidence", f"{stats['avg_confidence']*100:.1f}%")
                    st.metric("🔄 Total Accesses", stats["total_accesses"])
                    st.success("✅ Biomemetic Brain Active")
                    
                    # Memory reinforcement button
                    if st.button("🧠 Strengthen Memories"):
                        with st.spinner("Consolidating memories..."):
                            memory.reinforce_memories(DEFAULT_USER)
                        st.success("Memory reinforcement complete!")
                        st.rerun()
                        
                except Exception as e:
                    st.warning(f"Memory system issue: {str(e)}")
            else:
                st.info("💡 Using session memory only")
            
            st.markdown("---")
        
        # Simple chat interface
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        if prompt := st.chat_input("Share your thoughts with your Second Brain..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Store user message in Neo4j
            if memory:
                try:
                    memory.store_chat(DEFAULT_USER, "user", prompt)
                except Exception as e:
                    st.warning(f"Failed to store message: {str(e)}")
            
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get relevant memories for context
            context = []
            if memory:
                with st.spinner("🧠 Accessing memories..."):
                    try:
                        context = memory.get_relevant_memories(prompt, DEFAULT_USER)
                        if context:
                            st.success(f"🎯 Found {len(context)} relevant memories!")
                    except Exception as e:
                        st.warning(f"Memory retrieval issue: {str(e)}")
            
            # Get AI response with streaming
            with st.chat_message("assistant"):
                try:
                    # Build context string
                    context_str = "\n\n".join([f"- {mem}" for mem in context]) if context else ""
                    enhancements = " (Enhanced by your personal knowledge)" if context else ""
                    
                    context_section = f'Relevant Context from Knowledge Base:\n{context_str}' if context_str else ''
                    
                    system_prompt = f"""You are a sophisticated second brain assistant{enhancements} with access to the user's conversation history and knowledge.
                    
Your role is to:
1. Recall and reference past conversations naturally
2. Incorporate relevant knowledge from your memory
3. Provide thoughtful, contextual responses
4. Build on previous discussions to create continuity

{context_section}

You are an intelligent AI assistant designed to act as the user's second brain.
"""
                    
                    response = openai_client.chat.completions.create(
                        model="gpt-4o-mini-2024-07-18",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        stream=True,
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                    # Store AI response in Neo4j
                    if memory:
                        try:
                            memory.store_chat(DEFAULT_USER, "assistant", full_response)
                        except Exception as e:
                            st.warning(f"Failed to store AI response: {str(e)}")
                        
                except Exception as e:
                    st.error(f"AI Response Error: {str(e)}")
                    error_response = "I apologize, but I'm experiencing technical difficulties. Please check your OpenRouter API key and try again."
                    st.markdown(error_response)
                    st.session_state.messages.append({"role": "assistant", "content": error_response})

if __name__ == "__main__":
    main()