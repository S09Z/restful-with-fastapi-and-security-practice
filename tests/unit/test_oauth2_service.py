import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from authlib.integrations.base_client import OAuthError

from app.services.oauth2_service import OAuth2Service
from app.models import OAuthUser


class TestOAuth2Service:
    
    @pytest.fixture
    def oauth_service(self):
        return OAuth2Service()
    
    def test_generate_state(self, oauth_service):
        state1 = oauth_service.generate_state()
        state2 = oauth_service.generate_state()
        
        assert len(state1) > 20
        assert len(state2) > 20
        assert state1 != state2
    
    @pytest.mark.asyncio
    async def test_get_google_auth_url_success(self, oauth_service, override_settings):
        override_settings(
            GOOGLE_CLIENT_ID="test-client-id",
            GOOGLE_CLIENT_SECRET="test-client-secret"
        )
        
        oauth_service._setup_clients()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "authorization_endpoint": "https://accounts.google.com/oauth/authorize"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            oauth_service.google_client = AsyncMock()
            oauth_service.google_client.create_authorization_url.return_value = (
                "https://accounts.google.com/oauth/authorize?client_id=test"
            )
            
            auth_url = await oauth_service.get_google_auth_url(
                "http://localhost:8000/callback", 
                "test-state"
            )
            
            assert "https://accounts.google.com/oauth/authorize" in auth_url
    
    @pytest.mark.asyncio
    async def test_get_google_auth_url_not_configured(self, oauth_service, override_settings):
        override_settings(GOOGLE_CLIENT_ID=None, GOOGLE_CLIENT_SECRET=None)
        oauth_service._setup_clients()
        
        with pytest.raises(ValueError, match="Google OAuth2 not configured"):
            await oauth_service.get_google_auth_url("http://localhost:8000/callback", "test-state")
    
    @pytest.mark.asyncio
    async def test_get_github_auth_url_success(self, oauth_service, override_settings):
        override_settings(
            GITHUB_CLIENT_ID="test-client-id",
            GITHUB_CLIENT_SECRET="test-client-secret"
        )
        
        oauth_service._setup_clients()
        oauth_service.github_client = AsyncMock()
        oauth_service.github_client.create_authorization_url.return_value = (
            "https://github.com/login/oauth/authorize?client_id=test"
        )
        
        auth_url = await oauth_service.get_github_auth_url(
            "http://localhost:8000/callback", 
            "test-state"
        )
        
        assert "https://github.com/login/oauth/authorize" in auth_url
    
    @pytest.mark.asyncio
    async def test_get_github_auth_url_not_configured(self, oauth_service, override_settings):
        override_settings(GITHUB_CLIENT_ID=None, GITHUB_CLIENT_SECRET=None)
        oauth_service._setup_clients()
        
        with pytest.raises(ValueError, match="GitHub OAuth2 not configured"):
            await oauth_service.get_github_auth_url("http://localhost:8000/callback", "test-state")
    
    @pytest.mark.asyncio
    async def test_exchange_google_code_success(self, oauth_service, override_settings):
        override_settings(
            GOOGLE_CLIENT_ID="test-client-id",
            GOOGLE_CLIENT_SECRET="test-client-secret"
        )
        
        oauth_service._setup_clients()
        oauth_service.google_client = AsyncMock()
        
        # Mock discovery response
        mock_discovery_response = MagicMock()
        mock_discovery_response.json.return_value = {
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo"
        }
        
        # Mock token exchange
        oauth_service.google_client.fetch_token.return_value = {"access_token": "test-token"}
        
        # Mock user info response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "sub": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg"
        }
        oauth_service.google_client.get.return_value = mock_user_response
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_discovery_response
            
            oauth_user = await oauth_service.exchange_google_code(
                "test-code", 
                "http://localhost:8000/callback"
            )
            
            assert isinstance(oauth_user, OAuthUser)
            assert oauth_user.provider == "google"
            assert oauth_user.provider_id == "123456789"
            assert oauth_user.email == "test@example.com"
            assert oauth_user.full_name == "Test User"
            assert oauth_user.avatar_url == "https://example.com/avatar.jpg"
    
    @pytest.mark.asyncio
    async def test_exchange_github_code_success(self, oauth_service, override_settings):
        override_settings(
            GITHUB_CLIENT_ID="test-client-id",
            GITHUB_CLIENT_SECRET="test-client-secret"
        )
        
        oauth_service._setup_clients()
        oauth_service.github_client = AsyncMock()
        
        # Mock token exchange
        oauth_service.github_client.fetch_token.return_value = {"access_token": "test-token"}
        
        # Mock user and email responses
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": 123456789,
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg",
            "email": None
        }
        
        mock_emails_response = MagicMock()
        mock_emails_response.json.return_value = [
            {"email": "test@example.com", "primary": True, "verified": True}
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = mock_client.return_value.__aenter__.return_value
            mock_async_client.get.side_effect = [mock_user_response, mock_emails_response]
            
            oauth_user = await oauth_service.exchange_github_code(
                "test-code", 
                "http://localhost:8000/callback"
            )
            
            assert isinstance(oauth_user, OAuthUser)
            assert oauth_user.provider == "github"
            assert oauth_user.provider_id == "123456789"
            assert oauth_user.email == "test@example.com"
            assert oauth_user.full_name == "Test User"
            assert oauth_user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_exchange_google_code_failure(self, oauth_service, override_settings):
        override_settings(
            GOOGLE_CLIENT_ID="test-client-id",
            GOOGLE_CLIENT_SECRET="test-client-secret"
        )
        
        oauth_service._setup_clients()
        oauth_service.google_client = AsyncMock()
        oauth_service.google_client.fetch_token.side_effect = Exception("Token exchange failed")
        
        mock_discovery_response = MagicMock()
        mock_discovery_response.json.return_value = {
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_discovery_response
            
            with pytest.raises(OAuthError, match="Failed to exchange Google code"):
                await oauth_service.exchange_google_code(
                    "invalid-code", 
                    "http://localhost:8000/callback"
                )