from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.base_client import OAuthError
import httpx
from typing import Dict, Optional, Any
import secrets
from app.config import settings
from app.models import OAuthUser
import json


class OAuth2Service:
    def __init__(self):
        self.google_client = None
        self.github_client = None
        self._setup_clients()
    
    def _setup_clients(self):
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            self.google_client = AsyncOAuth2Client(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scope="openid email profile"
            )
        
        if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
            self.github_client = AsyncOAuth2Client(
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
                scope="user:email"
            )
    
    def generate_state(self) -> str:
        return secrets.token_urlsafe(32)
    
    async def get_google_auth_url(self, redirect_uri: str, state: str) -> str:
        if not self.google_client:
            raise ValueError("Google OAuth2 not configured")
        
        discovery_resp = await httpx.AsyncClient().get(settings.GOOGLE_DISCOVERY_URL)
        discovery_data = discovery_resp.json()
        authorization_endpoint = discovery_data["authorization_endpoint"]
        
        auth_url = await self.google_client.create_authorization_url(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            state=state,
            access_type="offline",
            prompt="select_account"
        )
        return auth_url
    
    async def get_github_auth_url(self, redirect_uri: str, state: str) -> str:
        if not self.github_client:
            raise ValueError("GitHub OAuth2 not configured")
        
        auth_url = await self.github_client.create_authorization_url(
            settings.GITHUB_AUTHORIZE_URL,
            redirect_uri=redirect_uri,
            state=state
        )
        return auth_url
    
    async def exchange_google_code(self, code: str, redirect_uri: str) -> OAuthUser:
        if not self.google_client:
            raise ValueError("Google OAuth2 not configured")
        
        try:
            discovery_resp = await httpx.AsyncClient().get(settings.GOOGLE_DISCOVERY_URL)
            discovery_data = discovery_resp.json()
            token_endpoint = discovery_data["token_endpoint"]
            userinfo_endpoint = discovery_data["userinfo_endpoint"]
            
            token = await self.google_client.fetch_token(
                token_endpoint,
                code=code,
                redirect_uri=redirect_uri
            )
            
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            resp = await self.google_client.get(userinfo_endpoint, headers=headers)
            user_info = resp.json()
            
            return OAuthUser(
                provider="google",
                provider_id=user_info["sub"],
                email=user_info["email"],
                full_name=user_info.get("name"),
                avatar_url=user_info.get("picture"),
                username=user_info.get("email").split("@")[0] if user_info.get("email") else None
            )
        except Exception as e:
            raise OAuthError(f"Failed to exchange Google code: {str(e)}")
    
    async def exchange_github_code(self, code: str, redirect_uri: str) -> OAuthUser:
        if not self.github_client:
            raise ValueError("GitHub OAuth2 not configured")
        
        try:
            token = await self.github_client.fetch_token(
                settings.GITHUB_TOKEN_URL,
                code=code,
                redirect_uri=redirect_uri
            )
            
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            
            async with httpx.AsyncClient() as client:
                user_resp = await client.get(settings.GITHUB_USER_URL, headers=headers)
                user_info = user_resp.json()
                
                emails_resp = await client.get(
                    "https://api.github.com/user/emails", 
                    headers=headers
                )
                emails = emails_resp.json()
                
                primary_email = next(
                    (email["email"] for email in emails if email["primary"]), 
                    user_info.get("email")
                )
            
            return OAuthUser(
                provider="github",
                provider_id=str(user_info["id"]),
                email=primary_email,
                full_name=user_info.get("name"),
                avatar_url=user_info.get("avatar_url"),
                username=user_info.get("login")
            )
        except Exception as e:
            raise OAuthError(f"Failed to exchange GitHub code: {str(e)}")


oauth2_service = OAuth2Service()