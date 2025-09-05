#!/usr/bin/env python3
"""
Test script to verify database integration with Prisma
"""
import asyncio
import os
from app.services.database_service import db_service
from app.models import OAuthUser

async def test_database_connection():
    """Test basic database connection"""
    print("🔗 Testing database connection...")
    
    try:
        await db_service.connect()
        print("✅ Database connected successfully")
        
        # Test creating a user
        oauth_user = OAuthUser(
            provider="google",
            provider_id="test-123456",
            email="test@example.com",
            full_name="Test User",
            username="testuser"
        )
        
        print("👤 Creating test user...")
        user = await db_service.create_user_with_oauth(oauth_user)
        print(f"✅ User created: {user.username} (ID: {user.id})")
        
        # Test retrieving user by OAuth provider
        print("🔍 Retrieving user by OAuth provider...")
        retrieved_user = await db_service.get_user_by_oauth_provider("google", "test-123456")
        if retrieved_user:
            print(f"✅ User retrieved: {retrieved_user.username}")
        else:
            print("❌ User not found")
        
        # Test creating session
        print("🎫 Creating session...")
        session_id = await db_service.create_session(user.id)
        print(f"✅ Session created: {session_id}")
        
        # Test retrieving session
        print("🔍 Retrieving session...")
        session_data = await db_service.get_session(session_id)
        if session_data:
            print(f"✅ Session retrieved: {session_data['username']}")
        else:
            print("❌ Session not found")
        
        # Test OAuth accounts
        print("🔗 Retrieving OAuth accounts...")
        accounts = await db_service.get_user_oauth_accounts(user.id)
        print(f"✅ OAuth accounts found: {len(accounts)}")
        for account in accounts:
            print(f"   - {account['provider']}: {account['provider_id']}")
        
        # Cleanup
        print("🧹 Cleaning up test data...")
        await db_service.delete_session(session_id)
        await db_service.delete_user(user.id)
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    finally:
        await db_service.disconnect()
        print("🔌 Database disconnected")
    
    return True

async def test_user_operations():
    """Test various user operations"""
    print("\n👥 Testing user operations...")
    
    await db_service.connect()
    
    try:
        # Create multiple users
        oauth_users = [
            OAuthUser(
                provider="google",
                provider_id="google-123",
                email="user1@gmail.com",
                full_name="Google User",
                username="googleuser"
            ),
            OAuthUser(
                provider="github", 
                provider_id="github-456",
                email="user2@github.com",
                full_name="GitHub User",
                username="githubuser"
            )
        ]
        
        created_users = []
        for oauth_user in oauth_users:
            user = await db_service.create_user_with_oauth(oauth_user)
            created_users.append(user)
            print(f"✅ Created user: {user.username} via {oauth_user.provider}")
        
        # Test linking additional OAuth account to existing user
        additional_oauth = OAuthUser(
            provider="github",
            provider_id="github-789",
            email="user1@gmail.com",  # Same email as first user
            full_name="Google User Alt",
            username="googleuser"
        )
        
        # This should link to existing user, not create new one
        existing_user = await db_service.get_user_by_email("user1@gmail.com")
        if existing_user:
            linked = await db_service.link_oauth_account(existing_user.id, additional_oauth)
            if linked:
                print("✅ Successfully linked additional OAuth account")
                accounts = await db_service.get_user_oauth_accounts(existing_user.id)
                print(f"   User now has {len(accounts)} OAuth accounts")
        
        # Cleanup
        for user in created_users:
            await db_service.delete_user(user.id)
        
        print("✅ User operations test completed")
        
    except Exception as e:
        print(f"❌ User operations test failed: {e}")
    finally:
        await db_service.disconnect()

async def main():
    """Main test function"""
    print("🚀 Starting database integration tests...\n")
    
    # Check if DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL environment variable not set")
        print("Please create a .env file with your database connection string")
        return
    
    # Run tests
    success = await test_database_connection()
    if success:
        await test_user_operations()
        print("\n✅ All database integration tests passed!")
    else:
        print("\n❌ Database integration tests failed!")

if __name__ == "__main__":
    asyncio.run(main())