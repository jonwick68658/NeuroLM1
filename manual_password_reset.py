#!/usr/bin/env python3
"""
Manual password reset for NeuroLM - Direct database access
"""

import os
import psycopg2
from passlib.context import CryptContext
import getpass

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

def manual_password_reset():
    """Manual password reset for specific user"""
    print("🔧 NeuroLM Manual Password Reset")
    print("=" * 50)
    
    # Get user input
    username = input("Enter username: ").strip()
    email = input("Enter email: ").strip()
    
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
            print("\nAvailable users:")
            cursor.execute("SELECT username, email FROM users ORDER BY created_at DESC")
            for u in cursor.fetchall():
                print(f"  - {u[0]} ({u[1]})")
            return False
        
        user_id, first_name, db_username, db_email = user
        print(f"✅ User found: {first_name} ({db_username})")
        print(f"   Email: {db_email}")
        print(f"   ID: {user_id}")
        
        # Get new password
        new_password = getpass.getpass("Enter new password: ")
        confirm_password = getpass.getpass("Confirm new password: ")
        
        if new_password != confirm_password:
            print("❌ Passwords do not match")
            return False
        
        if len(new_password) < 6:
            print("❌ Password must be at least 6 characters")
            return False
        
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
        print(f"🔗 You can now log in at: https://neuro-lm-79060699409.us-central1.run.app/login")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def verify_user_account():
    """Verify user account exists and show details"""
    print("🔍 User Account Verification")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Show all users
        cursor.execute("SELECT username, email, first_name, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        
        print("📋 All users in database:")
        for i, (username, email, first_name, created_at) in enumerate(users, 1):
            print(f"  {i}. {username} ({email}) - {first_name} - {created_at}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🚀 NeuroLM Account Management Tool")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. View all users")
        print("2. Reset password")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            verify_user_account()
        elif choice == "2":
            manual_password_reset()
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()