from fastapi import Header, HTTPException, Depends, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.security import decode_access_token
from app.services.redis_service import redis_client
from app.services.database_service import db_service
from app.models import User, TokenData
import json
from typing import Optional

security = HTTPBearer()

async def get_token_header(x_token: str = Header(...)):
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")

async def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        username = payload.get("username")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = User(
            id=int(user_id),
            username=username,
            email=email,
            is_active=True
        )
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_from_session(request: Request) -> Optional[User]:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    
    # Try database first
    session_data = await db_service.get_session(session_id)
    if session_data:
        return User(
            id=session_data["user_id"],
            username=session_data["username"],
            email=session_data.get("email"),
            is_active=True
        )
    
    # Fallback to Redis
    redis_session = await redis_client.get(f"session:{session_id}")
    if not redis_session:
        return None
    
    try:
        user_dict = json.loads(redis_session.decode())
        return User(
            id=user_dict["user_id"],
            username=user_dict["username"],
            email=user_dict.get("email"),
            is_active=True
        )
    except (json.JSONDecodeError, KeyError):
        return None

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    user = None
    
    if credentials:
        user = await get_current_user_from_token(credentials)
    
    if not user:
        user = await get_current_user_from_session(request)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None
