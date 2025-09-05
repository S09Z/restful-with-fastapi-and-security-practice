from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.user_routes import router as user_router
from app.api.v1.auth_routes import router as auth_router
from app.services.redis_service import redis_client
from app.services.database_service import db_service
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.connect()
    await db_service.connect()
    yield
    await redis_client.disconnect()
    await db_service.disconnect()

app = FastAPI(
    title="RESTful API with FastAPI and OAuth2",
    description="A secure RESTful API with OAuth2/OIDC authentication",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

@app.get("/")
async def read_root():
    return {
        "message": "RESTful API with OAuth2/OIDC Authentication",
        "docs": "/docs",
        "auth_endpoints": {
            "google_login": "/api/v1/auth/google/login",
            "github_login": "/api/v1/auth/github/login",
            "logout": "/api/v1/auth/logout",
            "me": "/api/v1/auth/me",
            "session": "/api/v1/auth/session"
        }
    }