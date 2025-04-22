import aioredis

from app.core.config import settings
from app.utils.logging_util import setup_logger


class RedisUtil:

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.redis = None

    async def connect(self):
        try:
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            self.logger.info('Connected to Redis')
        except aioredis.RedisError as e:
            self.logger.error(f"Error connecting to Redis: {e}")

    async def close(self):
        try:
            if self.redis:
                await self.redis.close()
                self.logger.info('Redis connection closed')
        except aioredis.RedisError as e:
            self.logger.error(f"Error closing Redis connection: {e}")

    async def get(self, key):
        try:
            if self.redis:
                value = await self.redis.get(key)
                self.logger.info(f"Retrieved value for key {key}: {value}")
                return value
            else:
                self.logger.error("Redis connection is not established")
                return None
        except aioredis.RedisError as e:
            self.logger.error(f"Error getting value for key {key}: {e}")
            return None

    async def set(self, key, value):
        try:
            if self.redis:
                await self.redis.set(key, value)
                self.logger.info(f"Set value for key {key}: {value}")
            else:
                self.logger.error("Redis connection is not established")
        except aioredis.RedisError as e:
            self.logger.error(f"Error setting value for key {key}: {e}")

    async def expire(self, key, seconds):
        try:
            if self.redis:
                await self.redis.expire(key, seconds)
                self.logger.info(f"Set expiry for key {key} to {seconds} seconds")
            else:
                self.logger.error("Redis connection is not established")
        except aioredis.RedisError as e:
            self.logger.error(f"Error setting expiry for key {key}: {e}")

    async def delete(self, key):
        try:
            if self.redis:
                result = await self.redis.delete(key)
                self.logger.info(f"Deleted key {key}, result: {result}")
                return result
            else:
                self.logger.error("Redis connection is not established")
                return None
        except aioredis.RedisError as e:
            self.logger.error(f"Error deleting key {key}: {e}")
            return None

    async def init_redis(self):
        await self.connect()


redis_util = RedisUtil()