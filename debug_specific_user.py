#!/usr/bin/env python3
"""
Debug specific user account issues
"""

import os
import psycopg2
from passlib.context import CryptContext
import hashlib

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def debug_user_account(username_or_email):
    """Debug specific user account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Search by username or email
        cursor.execute("""
            SELECT id, first_name, username, email, password_hash, created_at
            FROM users 
            WHERE username = %s OR email = %s
        """, (username_or_email, username_or_email))
        
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User not found: {username_or_email}")
            print("Available users:")
            cursor.execute("SELECT username, email FROM users ORDER BY created_at DESC")
            for u in cursor.fetchall():
                print(f"  - {u[0]} ({u[1]})")
        else:
            user_id, first_name, username, email, password_hash, created_at = user
            print(f"✅ User found: {username}")
            print(f"   ID: {user_id}")
            print(f"   Name: {first_name}")
            print(f"   Email: {email}")
            print(f"   Created: {created_at}")
            print(f"   Password hash type: {'BCrypt' if password_hash.startswith('$2b$') else 'Legacy SHA256'}")
            print(f"   Password hash preview: {password_hash[:20]}...")
            
            # Check for common password issues
            if not password_hash.startswith('$2b$'):
                print("   ⚠️  This user has a legacy SHA256 hash - requires exact original password")
            
            # Test a few common passwords (don't do this in production!)
            test_passwords = ["password", "123456", "admin", username, first_name.lower() if first_name else ""]
            print(f"\n🔍 Testing common passwords (for debugging only):")
            
            for test_pass in test_passwords:
                if test_pass:
                    if password_hash.startswith('$2b$'):
                        # BCrypt test
                        try:
                            if pwd_context.verify(test_pass, password_hash):
                                print(f"   ✅ MATCH: '{test_pass}' works with BCrypt")
                            else:
                                print(f"   ❌ No match: '{test_pass}'")
                        except Exception as e:
                            print(f"   ❌ Error testing '{test_pass}': {e}")
                    else:
                        # Legacy SHA256 test
                        legacy_hash = hashlib.sha256(test_pass.encode()).hexdigest()
                        if legacy_hash == password_hash:
                            print(f"   ✅ MATCH: '{test_pass}' works with legacy SHA256")
                        else:
                            print(f"   ❌ No match: '{test_pass}'")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error debugging user: {e}")

def main():
    print("🔍 NeuroLM User Account Debugger")
    print("=" * 50)
    
    # Debug all users first
    print("📋 All users in database:")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        for i, (username, email, created_at) in enumerate(users, 1):
            print(f"  {i}. {username} ({email}) - {created_at}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error listing users: {e}")
    
    print("\n" + "=" * 50)
    
    # Debug specific accounts that might be problematic
    test_accounts = ["Ryan", "ryantodd306@gmail.com", "testuser", "test@example.com"]
    
    for account in test_accounts:
        print(f"\n🔍 Debugging account: {account}")
        print("-" * 30)
        debug_user_account(account)

if __name__ == "__main__":
    main()