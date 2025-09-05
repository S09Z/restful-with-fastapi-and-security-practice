import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json

from app.main import app
from app.services.redis_service import redis_client, FakeRedisClient
from app.services.oauth2_service import oauth2_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_redis_client():
    fake_redis = FakeRedisClient()
    return fake_redis


@pytest.fixture
def mock_oauth2_service():
    service = MagicMock()
    service.generate_state.return_value = "test-state"
    service.get_google_auth_url = AsyncMock(return_value="https://google.com/auth?state=test")
    service.get_github_auth_url = AsyncMock(return_value="https://github.com/auth?state=test")
    service.exchange_google_code = AsyncMock()
    service.exchange_github_code = AsyncMock()
    return service


@pytest.fixture
def sample_oauth_user():
    from app.models import OAuthUser
    return OAuthUser(
        provider="google",
        provider_id="123456789",
        email="test@example.com",
        full_name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        username="testuser"
    )


@pytest.fixture
def sample_user():
    from app.models import User
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True
    )


@pytest.fixture
def valid_token():
    from app.security import create_access_token
    return create_access_token(data={"sub": "1", "username": "testuser", "email": "test@example.com"})


@pytest.fixture
def mock_httpx_client():
    client = AsyncMock()
    return client


@pytest_asyncio.fixture(autouse=True)
async def setup_test_environment():
    await redis_client.connect()
    redis_client.redis_client = FakeRedisClient()
    yield
    await redis_client.disconnect()


@pytest.fixture
def override_settings():
    from app.config import settings
    original_values = {}
    
    def _override(**kwargs):
        for key, value in kwargs.items():
            original_values[key] = getattr(settings, key, None)
            setattr(settings, key, value)
    
    yield _override
    
    for key, value in original_values.items():
        setattr(settings, key, value)