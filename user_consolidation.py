#!/usr/bin/env python3

import os
from neo4j import GraphDatabase

def consolidate_user_data():
    """Consolidate user data to ensure consistent user IDs across all systems"""
    
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )
    
    with driver.session() as session:
        # First, find all user IDs currently in the system
        print("=== CURRENT USER DATA ===")
        
        # Check Users table
        users = session.run("MATCH (u:User) RETURN u.id AS user_id, u.username AS username")
        user_list = list(users)
        print(f"Users in User table: {[u['user_id'] for u in user_list]}")
        
        # Check Memory data
        memory_users = session.run("MATCH (m:Memory) RETURN DISTINCT m.user_id AS user_id")
        memory_user_list = list(memory_users)
        print(f"User IDs in Memory: {[u['user_id'] for u in memory_user_list]}")
        
        # Check Document data
        doc_users = session.run("MATCH (d:Document) RETURN DISTINCT d.user_id AS user_id")
        doc_user_list = list(doc_users)
        print(f"User IDs in Documents: {[u['user_id'] for u in doc_user_list]}")
        
        # Check DocumentChunk data
        chunk_users = session.run("MATCH (c:DocumentChunk) RETURN DISTINCT c.user_id AS user_id")
        chunk_user_list = list(chunk_users)
        print(f"User IDs in DocumentChunks: {[u['user_id'] for u in chunk_user_list]}")
        
        # Find the primary user (the one with most data)
        all_user_ids = set()
        for users_data in [memory_user_list, doc_user_list, chunk_user_list]:
            for user in users_data:
                if user['user_id']:
                    all_user_ids.add(user['user_id'])
        
        print(f"All unique user IDs found: {list(all_user_ids)}")
        
        if len(all_user_ids) > 1:
            # Count data for each user ID to determine primary
            user_data_counts = {}
            for user_id in all_user_ids:
                memory_count = session.run("MATCH (m:Memory {user_id: $user_id}) RETURN count(m) AS count", user_id=user_id).single()['count']
                doc_count = session.run("MATCH (d:Document {user_id: $user_id}) RETURN count(d) AS count", user_id=user_id).single()['count']
                chunk_count = session.run("MATCH (c:DocumentChunk {user_id: $user_id}) RETURN count(c) AS count", user_id=user_id).single()['count']
                
                total_count = memory_count + doc_count + chunk_count
                user_data_counts[user_id] = {
                    'total': total_count,
                    'memories': memory_count,
                    'documents': doc_count,
                    'chunks': chunk_count
                }
                print(f"User {user_id}: {memory_count} memories, {doc_count} documents, {chunk_count} chunks (total: {total_count})")
            
            # Determine primary user (most data)
            primary_user = max(user_data_counts.keys(), key=lambda x: user_data_counts[x]['total'])
            print(f"Primary user determined: {primary_user}")
            
            # Consolidate all data under primary user
            for user_id in all_user_ids:
                if user_id != primary_user:
                    print(f"Consolidating {user_id} data under {primary_user}...")
                    
                    # Update memories
                    result = session.run("""
                    MATCH (m:Memory {user_id: $old_user_id})
                    SET m.user_id = $new_user_id
                    RETURN count(m) AS updated
                    """, old_user_id=user_id, new_user_id=primary_user)
                    memory_updated = result.single()['updated']
                    
                    # Update documents
                    result = session.run("""
                    MATCH (d:Document {user_id: $old_user_id})
                    SET d.user_id = $new_user_id
                    RETURN count(d) AS updated
                    """, old_user_id=user_id, new_user_id=primary_user)
                    doc_updated = result.single()['updated']
                    
                    # Update document chunks
                    result = session.run("""
                    MATCH (c:DocumentChunk {user_id: $old_user_id})
                    SET c.user_id = $new_user_id
                    RETURN count(c) AS updated
                    """, old_user_id=user_id, new_user_id=primary_user)
                    chunk_updated = result.single()['updated']
                    
                    print(f"  Updated: {memory_updated} memories, {doc_updated} documents, {chunk_updated} chunks")
            
            # Ensure primary user exists in User table
            existing_user = session.run("MATCH (u:User {id: $user_id}) RETURN u", user_id=primary_user).single()
            if not existing_user:
                print(f"Creating User record for {primary_user}")
                session.run("""
                CREATE (u:User {
                    id: $user_id,
                    username: $username,
                    created_at: datetime()
                })
                """, user_id=primary_user, username=primary_user.replace('user_', ''))
            
            print(f"User consolidation complete. All data now under: {primary_user}")
            return primary_user
        
        elif len(all_user_ids) == 1:
            primary_user = list(all_user_ids)[0]
            print(f"Single user found: {primary_user}")
            return primary_user
        
        else:
            print("No user data found")
            return None
    
    driver.close()

if __name__ == "__main__":
    primary_user = consolidate_user_data()
    if primary_user:
        print(f"\nFinal primary user: {primary_user}")
    else:
        print("\nNo user data to consolidate")