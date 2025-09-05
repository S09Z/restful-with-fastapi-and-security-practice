import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.models import OAuthUser


class TestAuthRoutes:
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_oauth_login_google_success(self, async_client, override_settings):
        override_settings(
            GOOGLE_CLIENT_ID="test-client-id",
            GOOGLE_CLIENT_SECRET="test-client-secret"
        )
        
        with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
            mock_service.generate_state.return_value = "test-state"
            mock_service.get_google_auth_url.return_value = "https://google.com/auth?state=test-state"
            
            response = await async_client.get("/api/v1/auth/google/login")
            
            assert response.status_code == 307  # Redirect
            assert "google.com/auth" in response.headers["location"]
    
    @pytest.mark.asyncio
    async def test_oauth_login_github_success(self, async_client, override_settings):
        override_settings(
            GITHUB_CLIENT_ID="test-client-id",
            GITHUB_CLIENT_SECRET="test-client-secret"
        )
        
        with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
            mock_service.generate_state.return_value = "test-state"
            mock_service.get_github_auth_url.return_value = "https://github.com/auth?state=test-state"
            
            response = await async_client.get("/api/v1/auth/github/login")
            
            assert response.status_code == 307  # Redirect
            assert "github.com/auth" in response.headers["location"]
    
    @pytest.mark.asyncio
    async def test_oauth_login_unsupported_provider(self, async_client):
        response = await async_client.get("/api/v1/auth/unsupported/login")
        
        assert response.status_code == 400
        assert "Unsupported OAuth provider" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_oauth_login_not_configured(self, async_client, override_settings):
        override_settings(GOOGLE_CLIENT_ID=None, GOOGLE_CLIENT_SECRET=None)
        
        with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
            mock_service.generate_state.return_value = "test-state"
            mock_service.get_google_auth_url.side_effect = ValueError("Google OAuth2 not configured")
            
            response = await async_client.get("/api/v1/auth/google/login")
            
            assert response.status_code == 500
            assert "not configured" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_oauth_callback_success(self, async_client, sample_oauth_user):
        # Mock Redis operations
        with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
            mock_redis.get.return_value = b"google"
            mock_redis.delete.return_value = True
            mock_redis.incr.return_value = 1
            mock_redis.set.return_value = True
            
            # Mock OAuth service
            with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
                mock_service.exchange_google_code.return_value = sample_oauth_user
                
                response = await async_client.get(
                    "/api/v1/auth/google/callback?code=test-code&state=test-state"
                )
                
                assert response.status_code == 307  # Redirect
                location = response.headers["location"]
                assert "token=" in location
                assert "session_id" in response.cookies
    
    @pytest.mark.asyncio
    async def test_oauth_callback_invalid_state(self, async_client):
        with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
            mock_redis.get.return_value = None
            
            response = await async_client.get(
                "/api/v1/auth/google/callback?code=test-code&state=invalid-state"
            )
            
            assert response.status_code == 400
            assert "Invalid state parameter" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_oauth_callback_error_parameter(self, async_client):
        response = await async_client.get(
            "/api/v1/auth/google/callback?error=access_denied&state=test-state"
        )
        
        assert response.status_code == 400
        assert "OAuth error: access_denied" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_oauth_callback_wrong_provider(self, async_client):
        with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
            mock_redis.get.return_value = b"github"
            mock_redis.delete.return_value = True
            
            response = await async_client.get(
                "/api/v1/auth/google/callback?code=test-code&state=test-state"
            )
            
            assert response.status_code == 400
            assert "Invalid state parameter" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_logout_success(self, async_client):
        # First, create a mock authenticated user
        with patch('app.dependencies.get_current_user') as mock_get_user:
            from app.models import User
            mock_get_user.return_value = User(
                id=1, username="testuser", email="test@example.com", is_active=True
            )
            
            with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
                mock_redis.delete.return_value = True
                
                # Set a session cookie
                async_client.cookies = {"session_id": "test-session-id"}
                
                response = await async_client.post("/api/v1/auth/logout")
                
                assert response.status_code == 200
                assert response.json()["message"] == "Logged out successfully"
    
    @pytest.mark.asyncio
    async def test_get_current_user_info(self, async_client):
        with patch('app.dependencies.get_current_user') as mock_get_user:
            from app.models import User
            test_user = User(
                id=1, 
                username="testuser", 
                email="test@example.com", 
                full_name="Test User",
                is_active=True
            )
            mock_get_user.return_value = test_user
            
            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            user_data = response.json()
            assert user_data["username"] == "testuser"
            assert user_data["email"] == "test@example.com"
            assert user_data["full_name"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_get_session_info_success(self, async_client):
        session_data = {
            "user_id": 1,
            "username": "testuser",
            "email": "test@example.com"
        }
        
        with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
            mock_redis.get.return_value = json.dumps(session_data).encode()
            
            response = await async_client.get(
                "/api/v1/auth/session",
                cookies={"session_id": "test-session-id"}
            )
            
            assert response.status_code == 200
            assert response.json() == session_data
    
    @pytest.mark.asyncio
    async def test_get_session_info_no_session(self, async_client):
        response = await async_client.get("/api/v1/auth/session")
        
        assert response.status_code == 401
        assert "No active session" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_session_info_expired(self, async_client):
        with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
            mock_redis.get.return_value = None
            
            response = await async_client.get(
                "/api/v1/auth/session",
                cookies={"session_id": "expired-session-id"}
            )
            
            assert response.status_code == 401
            assert "Session expired or invalid" in response.json()["detail"]