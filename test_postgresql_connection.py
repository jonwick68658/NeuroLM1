#!/usr/bin/env python3
"""
Test PostgreSQL connection and pgvector functionality
"""

import asyncio
import asyncpg
import os
from openai import OpenAI

async def test_postgresql_connection():
    """Test PostgreSQL connection and vector operations"""
    
    # Replace with your actual connection details
    DATABASE_URL = "postgresql://neurolm_user:YOUR_PASSWORD@34.44.233.216:5432/neurolm"
    
    print("Testing PostgreSQL connection...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to PostgreSQL")
        
        # Test basic query
        result = await conn.fetchval("SELECT version()")
        print(f"✅ PostgreSQL version: {result}")
        
        # Test pgvector
        result = await conn.fetchval("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector")
        print(f"✅ pgvector working: cosine distance = {result}")
        
        # Test table existence
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        print(f"✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table['tablename']}")
        
        # Test vector index
        indexes = await conn.fetch("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'intelligent_memories' 
            AND indexname LIKE '%embedding%'
        """)
        print(f"✅ Found {len(indexes)} vector indexes:")
        for idx in indexes:
            print(f"  - {idx['indexname']}")
        
        # Test embedding generation (if API key available)
        if os.getenv("OPENAI_API_KEY"):
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input="test embedding"
            )
            embedding = response.data[0].embedding
            print(f"✅ OpenAI embedding generated: {len(embedding)} dimensions")
            
            # Test storing and retrieving a vector
            await conn.execute("""
                INSERT INTO intelligent_memories 
                (user_id, content, message_type, embedding, importance, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
            """, "test_user", "test content", "test", embedding, 0.5)
            
            # Test vector similarity search
            similar = await conn.fetch("""
                SELECT content, 1 - (embedding <=> $1) as similarity
                FROM intelligent_memories
                WHERE user_id = $2
                ORDER BY similarity DESC
                LIMIT 1
            """, embedding, "test_user")
            
            if similar:
                print(f"✅ Vector similarity search working: {similar[0]['similarity']}")
            
            # Cleanup test data
            await conn.execute("DELETE FROM intelligent_memories WHERE user_id = $1", "test_user")
        
        await conn.close()
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_postgresql_connection())