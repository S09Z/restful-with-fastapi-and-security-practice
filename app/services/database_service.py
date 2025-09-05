from prisma import Prisma
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.models import User as UserModel, OAuthUser
from app.config import settings

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.db = Prisma()
    
    async def connect(self):
        """Connect to the database"""
        try:
            await self.db.connect()
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from the database"""
        try:
            await self.db.disconnect()
            logger.info("Disconnected from database")
        except Exception as e:
            logger.error(f"Failed to disconnect from database: {e}")

    async def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        """Get user by ID"""
        try:
            user = await self.db.user.find_unique(where={"id": user_id})
            if user:
                return UserModel(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    full_name=user.fullName,
                    is_active=user.isActive,
                    created_at=user.createdAt,
                    updated_at=user.updatedAt
                )
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email"""
        try:
            user = await self.db.user.find_unique(where={"email": email})
            if user:
                return UserModel(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    full_name=user.fullName,
                    is_active=user.isActive,
                    created_at=user.createdAt,
                    updated_at=user.updatedAt
                )
            return None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    async def get_user_by_oauth_provider(self, provider: str, provider_id: str) -> Optional[UserModel]:
        """Get user by OAuth provider and provider ID"""
        try:
            oauth_account = await self.db.oauthaccount.find_unique(
                where={"provider_providerId": {"provider": provider, "providerId": provider_id}},
                include={"user": True}
            )
            
            if oauth_account and oauth_account.user:
                user = oauth_account.user
                return UserModel(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    full_name=user.fullName,
                    is_active=user.isActive,
                    created_at=user.createdAt,
                    updated_at=user.updatedAt
                )
            return None
        except Exception as e:
            logger.error(f"Error getting user by OAuth {provider}:{provider_id}: {e}")
            return None

    async def create_user_with_oauth(self, oauth_user: OAuthUser) -> UserModel:
        """Create a new user with OAuth account"""
        try:
            # Create user and OAuth account in a transaction
            result = await self.db.user.create(
                data={
                    "username": oauth_user.username or oauth_user.email.split("@")[0],
                    "email": oauth_user.email,
                    "fullName": oauth_user.full_name,
                    "avatarUrl": oauth_user.avatar_url,
                    "isActive": True,
                    "oauthAccounts": {
                        "create": {
                            "provider": oauth_user.provider,
                            "providerId": oauth_user.provider_id,
                            "email": oauth_user.email
                        }
                    }
                }
            )
            
            return UserModel(
                id=result.id,
                username=result.username,
                email=result.email,
                full_name=result.fullName,
                is_active=result.isActive,
                created_at=result.createdAt,
                updated_at=result.updatedAt
            )
        except Exception as e:
            logger.error(f"Error creating user with OAuth: {e}")
            raise

    async def link_oauth_account(self, user_id: int, oauth_user: OAuthUser) -> bool:
        """Link an OAuth account to an existing user"""
        try:
            await self.db.oauthaccount.create(
                data={
                    "userId": user_id,
                    "provider": oauth_user.provider,
                    "providerId": oauth_user.provider_id,
                    "email": oauth_user.email
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error linking OAuth account to user {user_id}: {e}")
            return False

    async def update_oauth_account(self, provider: str, provider_id: str, access_token: str = None, refresh_token: str = None, expires_at: datetime = None) -> bool:
        """Update OAuth account tokens"""
        try:
            data = {}
            if access_token:
                data["accessToken"] = access_token
            if refresh_token:
                data["refreshToken"] = refresh_token
            if expires_at:
                data["expiresAt"] = expires_at
            
            if data:
                await self.db.oauthaccount.update(
                    where={"provider_providerId": {"provider": provider, "providerId": provider_id}},
                    data=data
                )
            return True
        except Exception as e:
            logger.error(f"Error updating OAuth account {provider}:{provider_id}: {e}")
            return False

    async def create_session(self, user_id: int, expires_at: datetime = None) -> str:
        """Create a new session for the user"""
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        try:
            session = await self.db.session.create(
                data={
                    "userId": user_id,
                    "expiresAt": expires_at
                }
            )
            return session.id
        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID"""
        try:
            session = await self.db.session.find_unique(
                where={"id": session_id},
                include={"user": True}
            )
            
            if session and session.expiresAt > datetime.utcnow():
                return {
                    "user_id": session.user.id,
                    "username": session.user.username,
                    "email": session.user.email,
                    "expires_at": session.expiresAt
                }
            return None
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            await self.db.session.delete(where={"id": session_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    async def delete_expired_sessions(self) -> int:
        """Delete all expired sessions"""
        try:
            result = await self.db.session.delete_many(
                where={"expiresAt": {"lt": datetime.utcnow()}}
            )
            return result
        except Exception as e:
            logger.error(f"Error deleting expired sessions: {e}")
            return 0

    async def get_user_oauth_accounts(self, user_id: int) -> List[dict]:
        """Get all OAuth accounts for a user"""
        try:
            accounts = await self.db.oauthaccount.find_many(
                where={"userId": user_id}
            )
            return [
                {
                    "provider": account.provider,
                    "provider_id": account.providerId,
                    "email": account.email,
                    "created_at": account.createdAt
                }
                for account in accounts
            ]
        except Exception as e:
            logger.error(f"Error getting OAuth accounts for user {user_id}: {e}")
            return []

    async def update_user(self, user_id: int, **kwargs) -> Optional[UserModel]:
        """Update user information"""
        try:
            data = {}
            if "username" in kwargs:
                data["username"] = kwargs["username"]
            if "email" in kwargs:
                data["email"] = kwargs["email"]
            if "full_name" in kwargs:
                data["fullName"] = kwargs["full_name"]
            if "avatar_url" in kwargs:
                data["avatarUrl"] = kwargs["avatar_url"]
            if "is_active" in kwargs:
                data["isActive"] = kwargs["is_active"]
            
            if data:
                user = await self.db.user.update(
                    where={"id": user_id},
                    data=data
                )
                return UserModel(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    full_name=user.fullName,
                    is_active=user.isActive,
                    created_at=user.createdAt,
                    updated_at=user.updatedAt
                )
            return None
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return None

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user and all associated data"""
        try:
            await self.db.user.delete(where={"id": user_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

# Global database service instance
db_service = DatabaseService()