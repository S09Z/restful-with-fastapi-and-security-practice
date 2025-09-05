from fastapi import APIRouter, Request, HTTPException, Depends, status, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from authlib.integrations.base_client import OAuthError
from app.services.oauth2_service import oauth2_service
from app.services.redis_service import redis_client
from app.services.database_service import db_service
from app.config import settings
from app.models import Token, OAuthUser, User
from app.security import create_access_token, decode_access_token
from app.dependencies import get_current_user
import json
from typing import Optional
import uuid

router = APIRouter()
security = HTTPBearer()

@router.get("/auth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    if provider not in ["google", "github"]:
        raise HTTPException(
            status_code=400, 
            detail="Unsupported OAuth provider"
        )
    
    state = oauth2_service.generate_state()
    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/{provider}/callback"
    
    await redis_client.set(f"oauth_state:{state}", provider, ex=300)
    
    try:
        if provider == "google":
            auth_url = await oauth2_service.get_google_auth_url(redirect_uri, state)
        elif provider == "github":
            auth_url = await oauth2_service.get_github_auth_url(redirect_uri, state)
        
        return RedirectResponse(auth_url)
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"OAuth provider {provider} not configured: {str(e)}"
        )

@router.get("/auth/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str, error: Optional[str] = None):
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth error: {error}"
        )
    
    stored_provider = await redis_client.get(f"oauth_state:{state}")
    if not stored_provider or stored_provider.decode() != provider:
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter"
        )
    
    await redis_client.delete(f"oauth_state:{state}")
    
    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/{provider}/callback"
    
    try:
        if provider == "google":
            oauth_user = await oauth2_service.exchange_google_code(code, redirect_uri)
        elif provider == "github":
            oauth_user = await oauth2_service.exchange_github_code(code, redirect_uri)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported OAuth provider"
            )
        
        user = await get_or_create_user(oauth_user)
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username, "email": user.email}
        )
        
        # Create database session
        session_id = await db_service.create_session(user.id)
        
        # Also store in Redis for quick access (optional fallback)
        await redis_client.set(
            f"session:{session_id}", 
            json.dumps({
                "user_id": user.id,
                "username": user.username,
                "email": user.email
            }),
            ex=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        response = RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        )
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        return response
        
    except OAuthError as e:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth authentication failed: {str(e)}"
        )

@router.post("/auth/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    session_id = request.cookies.get("session_id")
    if session_id:
        # Delete from both database and Redis
        await db_service.delete_session(session_id)
        await redis_client.delete(f"session:{session_id}")
    
    response = Response(content=json.dumps({"message": "Logged out successfully"}))
    response.delete_cookie("session_id")
    return response

@router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/auth/session")
async def get_session_info(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="No active session"
        )
    
    # Try database first, then Redis fallback
    session_data = await db_service.get_session(session_id)
    if not session_data:
        # Fallback to Redis
        redis_session = await redis_client.get(f"session:{session_id}")
        if redis_session:
            session_data = json.loads(redis_session.decode())
        else:
            raise HTTPException(
                status_code=401,
                detail="Session expired or invalid"
            )
    
    return session_data

async def get_or_create_user(oauth_user: OAuthUser) -> User:
    """Get existing user or create new user with OAuth account"""
    
    # First, try to find existing user by OAuth provider
    existing_user = await db_service.get_user_by_oauth_provider(
        oauth_user.provider, 
        oauth_user.provider_id
    )
    
    if existing_user:
        return existing_user
    
    # Check if user exists by email (for linking accounts)
    existing_user = await db_service.get_user_by_email(oauth_user.email)
    
    if existing_user:
        # Link OAuth account to existing user
        await db_service.link_oauth_account(existing_user.id, oauth_user)
        return existing_user
    
    # Create new user with OAuth account
    return await db_service.create_user_with_oauth(oauth_user)