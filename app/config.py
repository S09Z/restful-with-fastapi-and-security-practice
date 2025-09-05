import os
from typing import Optional

class Settings:
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OAuth2 Settings
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GITHUB_CLIENT_ID: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    
    # OAuth2 URLs
    GOOGLE_DISCOVERY_URL: str = "https://accounts.google.com/.well-known/openid_configuration"
    GITHUB_AUTHORIZE_URL: str = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL: str = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL: str = "https://api.github.com/user"
    
    # Application URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    
    # Ngrok support
    NGROK_URL: Optional[str] = os.getenv("NGROK_URL")
    
    @property
    def effective_backend_url(self) -> str:
        """Get the effective backend URL (ngrok if available, otherwise BACKEND_URL)"""
        return self.NGROK_URL or self.BACKEND_URL

settings = Settings()
