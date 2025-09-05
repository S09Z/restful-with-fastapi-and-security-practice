import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient

from app.main import app
from app.models import OAuthUser


class TestOAuthFlow:
    """Integration tests for the complete OAuth2 authentication flow."""
    
    @pytest.mark.asyncio
    async def test_complete_google_oauth_flow(self, override_settings):
        """Test complete Google OAuth2 flow from login to accessing protected resource."""
        override_settings(
            GOOGLE_CLIENT_ID="test-google-client-id",
            GOOGLE_CLIENT_SECRET="test-google-client-secret",
            FRONTEND_URL="http://localhost:3000",
            BACKEND_URL="http://localhost:8000"
        )
        
        oauth_user = OAuthUser(
            provider="google",
            provider_id="google-123456",
            email="testuser@gmail.com",
            full_name="Test Google User",
            avatar_url="https://google.com/avatar.jpg",
            username="testuser"
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Initiate OAuth login
            with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
                mock_service.generate_state.return_value = "test-state"
                mock_service.get_google_auth_url.return_value = "https://accounts.google.com/oauth/authorize?client_id=test"
                
                with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
                    mock_redis.set.return_value = True
                    
                    response = await client.get("/api/v1/auth/google/login")
                    
                    assert response.status_code == 307
                    assert "accounts.google.com" in response.headers["location"]
            
            # Step 2: Handle OAuth callback
            with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
                mock_service.exchange_google_code.return_value = oauth_user
                
                with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
                    mock_redis.get.return_value = b"google"
                    mock_redis.delete.return_value = True
                    mock_redis.incr.return_value = 1
                    mock_redis.set.return_value = True
                    
                    response = await client.get(
                        "/api/v1/auth/google/callback?code=test-code&state=test-state"
                    )
                    
                    assert response.status_code == 307
                    redirect_url = response.headers["location"]
                    assert "http://localhost:3000/auth/callback" in redirect_url
                    assert "token=" in redirect_url
                    
                    # Extract token from redirect URL
                    token = redirect_url.split("token=")[1]
                    session_id = response.cookies.get("session_id")
                    assert session_id is not None
            
            # Step 3: Access protected resource with token
            with patch('app.dependencies.redis_client') as mock_redis:
                session_data = {
                    "user_id": 1,
                    "username": "testuser",
                    "email": "testuser@gmail.com"
                }
                mock_redis.get.return_value = json.dumps(session_data).encode()
                
                response = await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                assert response.status_code == 200
                user_data = response.json()
                assert user_data["username"] == "testuser"
                assert user_data["email"] == "testuser@gmail.com"
            
            # Step 4: Access protected resource with session
            with patch('app.dependencies.redis_client') as mock_redis:
                session_data = {
                    "user_id": 1,
                    "username": "testuser",
                    "email": "testuser@gmail.com"
                }
                mock_redis.get.return_value = json.dumps(session_data).encode()
                
                response = await client.get(
                    "/api/v1/auth/session",
                    cookies={"session_id": session_id}
                )
                
                assert response.status_code == 200
                session_info = response.json()
                assert session_info["username"] == "testuser"
                assert session_info["email"] == "testuser@gmail.com"
            
            # Step 5: Logout
            with patch('app.dependencies.get_current_user') as mock_get_user:
                from app.models import User
                mock_get_user.return_value = User(
                    id=1,
                    username="testuser",
                    email="testuser@gmail.com",
                    is_active=True
                )
                
                with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
                    mock_redis.delete.return_value = True
                    
                    response = await client.post(
                        "/api/v1/auth/logout",
                        cookies={"session_id": session_id}
                    )
                    
                    assert response.status_code == 200
                    assert response.json()["message"] == "Logged out successfully"
    
    @pytest.mark.asyncio
    async def test_complete_github_oauth_flow(self, override_settings):
        """Test complete GitHub OAuth2 flow."""
        override_settings(
            GITHUB_CLIENT_ID="test-github-client-id",
            GITHUB_CLIENT_SECRET="test-github-client-secret"
        )
        
        oauth_user = OAuthUser(
            provider="github",
            provider_id="github-789012",
            email="testuser@github.com",
            full_name="Test GitHub User",
            avatar_url="https://github.com/avatar.jpg",
            username="githubuser"
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Initiate OAuth login
            with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
                mock_service.generate_state.return_value = "github-state"
                mock_service.get_github_auth_url.return_value = "https://github.com/login/oauth/authorize?client_id=test"
                
                with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
                    mock_redis.set.return_value = True
                    
                    response = await client.get("/api/v1/auth/github/login")
                    
                    assert response.status_code == 307
                    assert "github.com" in response.headers["location"]
            
            # Step 2: Handle OAuth callback
            with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
                mock_service.exchange_github_code.return_value = oauth_user
                
                with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
                    mock_redis.get.return_value = b"github"
                    mock_redis.delete.return_value = True
                    mock_redis.incr.return_value = 2
                    mock_redis.set.return_value = True
                    
                    response = await client.get(
                        "/api/v1/auth/github/callback?code=github-code&state=github-state"
                    )
                    
                    assert response.status_code == 307
                    redirect_url = response.headers["location"]
                    assert "token=" in redirect_url
    
    @pytest.mark.asyncio
    async def test_oauth_error_handling(self, override_settings):
        """Test OAuth error handling throughout the flow."""
        override_settings(
            GOOGLE_CLIENT_ID="test-client-id",
            GOOGLE_CLIENT_SECRET="test-client-secret"
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test invalid state parameter
            with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
                mock_redis.get.return_value = None
                
                response = await client.get(
                    "/api/v1/auth/google/callback?code=test-code&state=invalid-state"
                )
                
                assert response.status_code == 400
                assert "Invalid state parameter" in response.json()["detail"]
            
            # Test OAuth error parameter
            response = await client.get(
                "/api/v1/auth/google/callback?error=access_denied&state=test-state"
            )
            
            assert response.status_code == 400
            assert "access_denied" in response.json()["detail"]
            
            # Test OAuth service failure
            with patch('app.api.v1.auth_routes.oauth2_service') as mock_service:
                from authlib.integrations.base_client import OAuthError
                mock_service.exchange_google_code.side_effect = OAuthError("Token exchange failed")
                
                with patch('app.api.v1.auth_routes.redis_client') as mock_redis:
                    mock_redis.get.return_value = b"google"
                    mock_redis.delete.return_value = True
                    
                    response = await client.get(
                        "/api/v1/auth/google/callback?code=invalid-code&state=test-state"
                    )
                    
                    assert response.status_code == 400
                    assert "OAuth authentication failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_authentication_middleware_integration(self):
        """Test that authentication middleware works with various endpoints."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test accessing protected endpoint without authentication
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 401
            
            # Test with invalid token
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid-token"}
            )
            assert response.status_code == 401
            
            # Test with valid token
            from app.security import create_access_token
            token = create_access_token(data={
                "sub": "1",
                "username": "testuser",
                "email": "test@example.com"
            })
            
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200