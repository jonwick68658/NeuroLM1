#!/usr/bin/env python3
"""
Direct password reset for Ryan's account
"""

import os
import psycopg2
from passlib.context import CryptContext

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

def reset_password():
    """Reset password for Ryan's account"""
    username = "Ryan"
    email = "ryantodd306@gmail.com"
    new_password = "test123456"  # Temporary password - change after login
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify user exists
        cursor.execute(
            "SELECT id, first_name, username, email FROM users WHERE username = %s AND email = %s",
            (username, email)
        )
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User not found with username '{username}' and email '{email}'")
            # Show all users
            cursor.execute("SELECT username, email, first_name FROM users ORDER BY created_at DESC")
            users = cursor.fetchall()
            print("Available users:")
            for u in users:
                print(f"  - {u[0]} ({u[1]}) - {u[2]}")
            return False
        
        user_id, first_name, db_username, db_email = user
        print(f"✅ User found: {first_name} ({db_username})")
        print(f"   Email: {db_email}")
        print(f"   ID: {user_id}")
        
        # Hash new password
        new_password_hash = pwd_context.hash(new_password)
        print(f"✅ Password hashed successfully")
        
        # Update password in database
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_password_hash, user_id)
        )
        conn.commit()
        
        print(f"✅ Password updated successfully for user '{username}'")
        print(f"🔑 New password: {new_password}")
        print(f"🔗 Login at: https://neuro-lm-79060699409.us-central1.run.app/login")
        print(f"⚠️  Remember to change this password after logging in!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Resetting Ryan's password...")
    reset_password()