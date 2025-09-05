import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import (
    get_current_user_from_token,
    get_current_user_from_session,
    get_current_user,
    get_optional_current_user
)
from app.models import User


class TestDependencies:
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_token_success(self, valid_token):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )
        
        user = await get_current_user_from_token(credentials)
        
        assert isinstance(user, User)
        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active == True
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_token_invalid(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_token(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_token_no_user_id(self):
        from app.security import create_access_token
        
        # Create token without 'sub' field
        token = create_access_token(data={"username": "testuser"})
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_from_token(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token: missing user ID" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_session_success(self):
        session_data = {
            "user_id": 1,
            "username": "testuser",
            "email": "test@example.com"
        }
        
        # Create a mock request with session cookie
        request = MagicMock()
        request.cookies = {"session_id": "test-session-id"}
        
        with patch('app.dependencies.redis_client') as mock_redis:
            mock_redis.get.return_value = json.dumps(session_data).encode()
            
            user = await get_current_user_from_session(request)
            
            assert isinstance(user, User)
            assert user.id == 1
            assert user.username == "testuser"
            assert user.email == "test@example.com"
            assert user.is_active == True
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_session_no_cookie(self):
        request = MagicMock()
        request.cookies = {}
        
        user = await get_current_user_from_session(request)
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_session_expired(self):
        request = MagicMock()
        request.cookies = {"session_id": "expired-session-id"}
        
        with patch('app.dependencies.redis_client') as mock_redis:
            mock_redis.get.return_value = None
            
            user = await get_current_user_from_session(request)
            
            assert user is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_from_session_invalid_json(self):
        request = MagicMock()
        request.cookies = {"session_id": "test-session-id"}
        
        with patch('app.dependencies.redis_client') as mock_redis:
            mock_redis.get.return_value = b"invalid-json"
            
            user = await get_current_user_from_session(request)
            
            assert user is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_token_priority(self, valid_token):
        # Both token and session are available, token should take priority
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )
        
        request = MagicMock()
        request.cookies = {"session_id": "test-session-id"}
        
        session_data = {
            "user_id": 999,  # Different user ID
            "username": "sessionuser",
            "email": "session@example.com"
        }
        
        with patch('app.dependencies.redis_client') as mock_redis:
            mock_redis.get.return_value = json.dumps(session_data).encode()
            
            user = await get_current_user(request, credentials)
            
            # Should return token user, not session user
            assert user.id == 1
            assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_current_user_session_fallback(self):
        # Invalid token, should fallback to session
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token"
        )
        
        request = MagicMock()
        request.cookies = {"session_id": "test-session-id"}
        
        session_data = {
            "user_id": 1,
            "username": "testuser",
            "email": "test@example.com"
        }
        
        with patch('app.dependencies.redis_client') as mock_redis:
            mock_redis.get.return_value = json.dumps(session_data).encode()
            
            user = await get_current_user(request, credentials)
            
            assert user.id == 1
            assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_authentication(self):
        request = MagicMock()
        request.cookies = {}
        
        credentials = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, credentials)
        
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_optional_current_user_success(self, valid_token):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_token
        )
        
        request = MagicMock()
        request.cookies = {}
        
        user = await get_optional_current_user(request, credentials)
        
        assert isinstance(user, User)
        assert user.id == 1
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_optional_current_user_no_auth(self):
        request = MagicMock()
        request.cookies = {}
        
        credentials = None
        
        user = await get_optional_current_user(request, credentials)
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_optional_current_user_invalid_token(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token"
        )
        
        request = MagicMock()
        request.cookies = {}
        
        user = await get_optional_current_user(request, credentials)
        
        assert user is None