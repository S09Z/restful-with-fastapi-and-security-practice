import redis.asyncio as redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_pool = None
        self.redis_client = None
    
    async def connect(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = FakeRedisClient()
    
    async def disconnect(self):
        if self.redis_client and hasattr(self.redis_client, 'close'):
            await self.redis_client.close()
    
    async def set(self, key: str, value: str, ex: int = None):
        if self.redis_client:
            return await self.redis_client.set(key, value, ex=ex)
        return None
    
    async def get(self, key: str):
        if self.redis_client:
            return await self.redis_client.get(key)
        return None
    
    async def delete(self, key: str):
        if self.redis_client:
            return await self.redis_client.delete(key)
        return None
    
    async def incr(self, key: str):
        if self.redis_client:
            return await self.redis_client.incr(key)
        return 1

class FakeRedisClient:
    def __init__(self):
        self._data = {}
        self._counters = {}
    
    async def set(self, key: str, value: str, ex: int = None):
        self._data[key] = value
        return True
    
    async def get(self, key: str):
        value = self._data.get(key)
        return value.encode() if value else None
    
    async def delete(self, key: str):
        if key in self._data:
            del self._data[key]
        return True
    
    async def incr(self, key: str):
        if key not in self._counters:
            self._counters[key] = 0
        self._counters[key] += 1
        return self._counters[key]

redis_client = RedisClient()