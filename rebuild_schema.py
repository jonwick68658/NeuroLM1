#!/usr/bin/env python3
"""
Complete NeuroLM Database Schema Rebuild
Systematic reconstruction of the Neo4j database with proper relationships and constraints
"""

import os
from neo4j import GraphDatabase
from datetime import datetime
import json

class SchemaRebuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
    
    def step1_clear_database(self):
        """Step 1: Complete database wipe"""
        print("🔥 STEP 1: Clearing entire database...")
        
        with self.driver.session() as session:
            # Delete all relationships first
            result = session.run("MATCH ()-[r]-() DELETE r")
            print(f"   Deleted relationships")
            
            # Delete all nodes
            result = session.run("MATCH (n) DELETE n")
            print(f"   Deleted all nodes")
            
            # Drop all indexes and constraints
            constraints = session.run("SHOW CONSTRAINTS").data()
            for constraint in constraints:
                try:
                    session.run(f"DROP CONSTRAINT {constraint['name']}")
                    print(f"   Dropped constraint: {constraint['name']}")
                except:
                    pass
            
            indexes = session.run("SHOW INDEXES").data()
            for index in indexes:
                try:
                    if index['name'] != 'btree_User_id':  # Skip if it's the one we'll recreate
                        session.run(f"DROP INDEX {index['name']}")
                        print(f"   Dropped index: {index['name']}")
                except:
                    pass
        
        print("✅ Database completely cleared")
        return True
    
    def step2_create_schema(self):
        """Step 2: Create optimized schema with proper constraints"""
        print("🏗️  STEP 2: Creating new optimized schema...")
        
        with self.driver.session() as session:
            # User constraints
            session.run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            print("   ✓ User ID unique constraint")
            
            # Memory node constraints and indexes
            session.run("CREATE INDEX memory_user_id IF NOT EXISTS FOR (m:Memory) ON (m.user_id)")
            session.run("CREATE INDEX memory_timestamp IF NOT EXISTS FOR (m:Memory) ON (m.timestamp)")
            session.run("CREATE INDEX memory_role IF NOT EXISTS FOR (m:Memory) ON (m.role)")
            print("   ✓ Memory indexes")
            
            # Document constraints
            session.run("CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
            session.run("CREATE INDEX document_user_id IF NOT EXISTS FOR (d:Document) ON (d.user_id)")
            print("   ✓ Document constraints")
            
            # DocumentChunk indexes
            session.run("CREATE INDEX chunk_user_id IF NOT EXISTS FOR (c:DocumentChunk) ON (c.user_id)")
            session.run("CREATE INDEX chunk_filename IF NOT EXISTS FOR (c:DocumentChunk) ON (c.filename)")
            session.run("CREATE INDEX chunk_doc_id IF NOT EXISTS FOR (c:DocumentChunk) ON (c.doc_id)")
            print("   ✓ DocumentChunk indexes")
            
            # Topic indexes
            session.run("CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.name)")
            session.run("CREATE INDEX topic_user_id IF NOT EXISTS FOR (t:Topic) ON (t.user_id)")
            print("   ✓ Topic indexes")
            
            # Vector similarity indexes for embeddings
            try:
                # Memory embeddings vector index
                session.run("""
                CREATE VECTOR INDEX memory_embeddings IF NOT EXISTS
                FOR (m:Memory) ON (m.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
                """)
                print("   ✓ Memory vector index")
                
                # DocumentChunk embeddings vector index  
                session.run("""
                CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
                FOR (c:DocumentChunk) ON (c.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
                """)
                print("   ✓ DocumentChunk vector index")
                
            except Exception as e:
                print(f"   ⚠️  Vector indexes may need Neo4j 5.x: {e}")
        
        print("✅ Schema created successfully")
        return True
    
    def step3_verify_schema(self):
        """Step 3: Verify schema was created correctly"""
        print("🔍 STEP 3: Verifying schema...")
        
        with self.driver.session() as session:
            # Check constraints
            constraints = session.run("SHOW CONSTRAINTS").data()
            print(f"   Constraints created: {len(constraints)}")
            for constraint in constraints:
                print(f"     - {constraint['name']}")
            
            # Check indexes
            indexes = session.run("SHOW INDEXES").data()
            print(f"   Indexes created: {len(indexes)}")
            for index in indexes:
                print(f"     - {index['name']}")
        
        print("✅ Schema verification complete")
        return True
    
    def step4_create_test_user(self):
        """Step 4: Create test user node"""
        print("👤 STEP 4: Creating test user...")
        
        with self.driver.session() as session:
            result = session.run("""
            CREATE (u:User {
                id: 'user_Ryan',
                name: 'Ryan',
                created_at: datetime(),
                last_active: datetime()
            })
            RETURN u.id as user_id
            """)
            
            user_record = result.single()
            if user_record:
                print(f"   ✓ Created user: {user_record['user_id']}")
            else:
                print("   ❌ Failed to create user")
                return False
        
        print("✅ Test user created")
        return True
    
    def run_full_rebuild(self):
        """Execute complete rebuild process"""
        print("=" * 60)
        print("🚀 STARTING NEUROLM DATABASE REBUILD")
        print("=" * 60)
        
        steps = [
            self.step1_clear_database,
            self.step2_create_schema, 
            self.step3_verify_schema,
            self.step4_create_test_user
        ]
        
        for i, step in enumerate(steps, 1):
            try:
                success = step()
                if not success:
                    print(f"❌ FAILED at step {i}")
                    return False
                print()
            except Exception as e:
                print(f"❌ ERROR in step {i}: {str(e)}")
                return False
        
        print("=" * 60)
        print("🎉 DATABASE REBUILD COMPLETE!")
        print("=" * 60)
        return True
    
    def close(self):
        self.driver.close()

if __name__ == "__main__":
    rebuilder = SchemaRebuilder()
    try:
        success = rebuilder.run_full_rebuild()
        if success:
            print("\n✅ Ready for Phase 2: Core Systems Integration")
        else:
            print("\n❌ Rebuild failed - check errors above")
    finally:
        rebuilder.close()