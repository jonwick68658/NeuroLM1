#!/usr/bin/env python3
"""
Test authentication system for NeuroLM
"""

import os
import psycopg2
from passlib.context import CryptContext
from main import verify_user_login, create_user_in_db, hash_password, get_db_connection

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_database_connection():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"✅ Database connection successful - {user_count} users found")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_existing_user_authentication():
    """Test authentication for existing users"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get first user with BCrypt hash
        cursor.execute("SELECT username, password_hash FROM users WHERE password_hash LIKE '$2b$%' LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            username, password_hash = result
            print(f"✅ Found test user: {username}")
            print(f"✅ Password hash type: {'BCrypt' if password_hash.startswith('$2b$') else 'Legacy'}")
            
            # Test with wrong password
            user_id = verify_user_login(username, "wrongpassword")
            if user_id:
                print(f"❌ Authentication failed: wrong password should not work")
                return False
            else:
                print(f"✅ Authentication correctly rejected wrong password")
            
            cursor.close()
            conn.close()
            return True
        else:
            print("❌ No BCrypt users found for testing")
            cursor.close()
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

def test_new_user_registration():
    """Test new user registration"""
    try:
        test_username = "test_auth_user"
        test_email = "test_auth@example.com"
        test_password = "TestPassword123!"
        
        # First, clean up any existing test user
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s OR email = %s", (test_username, test_email))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Test registration
        password_hash = hash_password(test_password)
        success = create_user_in_db("Test", test_username, test_email, password_hash)
        
        if success:
            print(f"✅ New user registration successful")
            
            # Test login with new user
            user_id = verify_user_login(test_username, test_password)
            if user_id:
                print(f"✅ New user login successful")
                
                # Clean up test user
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = %s", (test_username,))
                conn.commit()
                cursor.close()
                conn.close()
                print(f"✅ Test user cleaned up")
                
                return True
            else:
                print(f"❌ New user login failed")
                return False
        else:
            print(f"❌ New user registration failed")
            return False
            
    except Exception as e:
        print(f"❌ Registration test failed: {e}")
        return False

def main():
    print("🔍 Testing NeuroLM Authentication System")
    print("=" * 50)
    
    # Test database connection
    if not test_database_connection():
        return
    
    # Test existing user authentication
    print("\n🔐 Testing existing user authentication...")
    test_existing_user_authentication()
    
    # Test new user registration
    print("\n👤 Testing new user registration...")
    test_new_user_registration()
    
    print("\n" + "=" * 50)
    print("✅ Authentication system tests completed")

if __name__ == "__main__":
    main()