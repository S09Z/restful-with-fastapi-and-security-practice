# Database Integration with Prisma

This guide explains how to use the Prisma database integration for OAuth2 user management in your FastAPI application.

## Overview

The application now uses PostgreSQL as the primary database with Prisma as the ORM, while maintaining Redis for caching and session backup.

## Database Models

### User Model
```sql
users (
  id: SERIAL PRIMARY KEY,
  username: VARCHAR UNIQUE,
  email: VARCHAR UNIQUE,
  full_name: VARCHAR,
  avatar_url: VARCHAR,
  is_active: BOOLEAN DEFAULT true,
  created_at: TIMESTAMP DEFAULT NOW(),
  updated_at: TIMESTAMP DEFAULT NOW()
)
```

### OAuth Account Model
```sql
oauth_accounts (
  id: SERIAL PRIMARY KEY,
  user_id: INT REFERENCES users(id) ON DELETE CASCADE,
  provider: VARCHAR, -- 'google', 'github', etc.
  provider_id: VARCHAR, -- OAuth provider's user ID
  email: VARCHAR,
  access_token: VARCHAR,
  refresh_token: VARCHAR,
  expires_at: TIMESTAMP,
  created_at: TIMESTAMP DEFAULT NOW(),
  updated_at: TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(provider, provider_id),
  UNIQUE(provider, user_id)
)
```

### Session Model
```sql
sessions (
  id: UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id: INT REFERENCES users(id) ON DELETE CASCADE,
  expires_at: TIMESTAMP,
  created_at: TIMESTAMP DEFAULT NOW(),
  updated_at: TIMESTAMP DEFAULT NOW()
)
```

## Setup Instructions

### 1. Database Configuration

Create a `.env` file with your database connection:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/oauth_db

# Other OAuth2 settings...
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### 2. Database Setup

```bash
# Generate Prisma client
poetry run prisma generate

# Run database migrations
poetry run prisma migrate dev --name "initial_migration"

# Or deploy to production
poetry run prisma migrate deploy
```

### 3. Test Database Connection

```bash
python test_db_integration.py
```

## Usage Examples

### Using the Database Service

```python
from app.services.database_service import db_service

# Create user with OAuth account
oauth_user = OAuthUser(
    provider="google",
    provider_id="123456789",
    email="user@example.com",
    full_name="John Doe",
    username="johndoe"
)

user = await db_service.create_user_with_oauth(oauth_user)

# Get user by OAuth provider
user = await db_service.get_user_by_oauth_provider("google", "123456789")

# Get user by email
user = await db_service.get_user_by_email("user@example.com")

# Create session
session_id = await db_service.create_session(user.id)

# Get session
session_data = await db_service.get_session(session_id)
```

### OAuth2 Flow Integration

The OAuth2 authentication flow now automatically:

1. **Creates or finds users** in the database
2. **Links OAuth accounts** to existing users when emails match
3. **Stores sessions** in both database and Redis
4. **Maintains data consistency** between providers

### Account Linking

When a user signs in with different OAuth providers using the same email:

```python
# User signs in with Google first
google_oauth = OAuthUser(
    provider="google",
    provider_id="google-123",
    email="user@example.com",
    # ... other fields
)
user = await db_service.create_user_with_oauth(google_oauth)

# Same user signs in with GitHub later
github_oauth = OAuthUser(
    provider="github", 
    provider_id="github-456",
    email="user@example.com",  # Same email
    # ... other fields
)

# This will link the GitHub account to the existing user
existing_user = await db_service.get_user_by_email("user@example.com")
await db_service.link_oauth_account(existing_user.id, github_oauth)
```

## Database Operations

### User Management

```python
# Update user information
updated_user = await db_service.update_user(
    user_id=1,
    full_name="New Name",
    avatar_url="https://example.com/new-avatar.jpg"
)

# Get user's OAuth accounts
accounts = await db_service.get_user_oauth_accounts(user_id=1)

# Soft delete user
await db_service.update_user(user_id=1, is_active=False)

# Hard delete user (removes all associated data)
await db_service.delete_user(user_id=1)
```

### Session Management

```python
# Create session with custom expiration
from datetime import datetime, timedelta
expires_at = datetime.utcnow() + timedelta(hours=24)
session_id = await db_service.create_session(user_id=1, expires_at=expires_at)

# Delete specific session
await db_service.delete_session(session_id)

# Clean up expired sessions
deleted_count = await db_service.delete_expired_sessions()
```

### OAuth Token Management

```python
from datetime import datetime, timedelta

# Update OAuth tokens
expires_at = datetime.utcnow() + timedelta(hours=1)
await db_service.update_oauth_account(
    provider="google",
    provider_id="123456789",
    access_token="new_access_token",
    refresh_token="new_refresh_token",  
    expires_at=expires_at
)
```

## Migration Commands

### Development

```bash
# Create new migration
poetry run prisma migrate dev --name "add_new_field"

# Reset database (WARNING: deletes all data)
poetry run prisma migrate reset

# View migration status
poetry run prisma migrate status
```

### Production

```bash
# Deploy migrations to production
poetry run prisma migrate deploy

# Generate Prisma client in production
poetry run prisma generate
```

## Backup and Maintenance

### Database Backup

```bash
# Backup database
pg_dump postgresql://username:password@localhost:5432/oauth_db > backup.sql

# Restore database
psql postgresql://username:password@localhost:5432/oauth_db < backup.sql
```

### Cleanup Scheduled Tasks

Consider running these periodically:

```python
# Clean expired sessions (run daily)
deleted_sessions = await db_service.delete_expired_sessions()

# Clean expired refresh tokens (if implemented)
# await db_service.delete_expired_refresh_tokens()
```

## Monitoring and Logging

The database service includes comprehensive logging:

```python
import logging

# Configure logging level
logging.getLogger('app.services.database_service').setLevel(logging.INFO)
```

Key events logged:
- Database connections/disconnections
- User creation and updates
- Session management
- OAuth account linking
- Error conditions

## Performance Considerations

1. **Indexes**: The schema includes optimized indexes for common queries
2. **Connection Pooling**: Prisma handles connection pooling automatically
3. **Redis Fallback**: Sessions are cached in Redis for faster access
4. **Async Operations**: All database operations are async for better performance

## Troubleshooting

### Common Issues

1. **Connection refused**: Check DATABASE_URL and PostgreSQL service
2. **Migration errors**: Ensure database schema is up to date
3. **Unique constraint violations**: Handle duplicate emails/usernames gracefully
4. **Session not found**: Sessions expire automatically, implement proper error handling

### Debug Mode

Set environment variable for detailed Prisma logs:

```bash
DEBUG="prisma:*" python your_app.py
```

## Security Considerations

1. **Connection Strings**: Never commit DATABASE_URL to version control
2. **SQL Injection**: Prisma provides built-in protection
3. **Data Validation**: All inputs are validated through Pydantic models
4. **Access Control**: Database operations are restricted to authenticated users
5. **Token Storage**: OAuth tokens are encrypted and properly secured