"""
Redis Caching Layer

Architectural Intent:
- Distributed caching for sessions and queries
- Redis-based cache with TTL support
- Cache invalidation patterns
"""

from typing import Optional, Any, Dict, List
from dataclasses import dataclass
import json
import hashlib
from enum import Enum
import redis.asyncio as redis


class CacheTier(Enum):
    SESSION = "session"
    QUERY = "query"
    COMPUTED = "computed"
    STATIC = "static"


@dataclass
class CacheConfig:
    ttl: int = 3600
    max_size: int = 1000
    compress: bool = False


class RedisCache:
    """Async Redis caching layer."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None
        self._configs: Dict[CacheTier, CacheConfig] = {
            CacheTier.SESSION: CacheConfig(ttl=86400),
            CacheTier.QUERY: CacheConfig(ttl=300),
            CacheTier.COMPUTED: CacheConfig(ttl=1800),
            CacheTier.STATIC: CacheConfig(ttl=3600),
        }

    async def connect(self):
        self._client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self):
        if self._client:
            await self._client.close()

    async def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        tier: CacheTier = CacheTier.QUERY,
        ttl: int = None,
    ):
        if not self._client:
            return

        config = self._configs.get(tier, CacheConfig())
        ttl = ttl or config.ttl

        try:
            serialized = json.dumps(value)
            await self._client.setex(key, ttl, serialized)
        except Exception as e:
            print(f"Cache set error: {e}")

    async def delete(self, key: str):
        if self._client:
            await self._client.delete(key)

    async def delete_pattern(self, pattern: str):
        if not self._client:
            return

        cursor = 0
        while True:
            cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
            if keys:
                await self._client.delete(*keys)
            if cursor == 0:
                break

    async def invalidate_entity(self, entity_type: str, entity_id: str):
        await self.delete_pattern(f"*{entity_type}:{entity_id}*")

    def generate_key(
        self,
        tier: CacheTier,
        org_id: str,
        *parts,
    ) -> str:
        parts_str = ":".join(str(p) for p in parts)
        key_hash = hashlib.sha256(parts_str.encode()).hexdigest()[:12]
        return f"nexus:{tier.value}:{org_id}:{key_hash}"

    async def get_session(self, session_id: str) -> Optional[Dict]:
        return await self.get(f"nexus:session:{session_id}")

    async def set_session(self, session_id: str, data: Dict, ttl: int = 86400):
        await self.set(f"nexus:session:{session_id}", data, CacheTier.SESSION, ttl)

    async def delete_session(self, session_id: str):
        await self.delete(f"nexus:session:{session_id}")

    async def get_cached_query(self, query_key: str) -> Optional[List]:
        return await self.get(query_key)

    async def cache_query(self, query_key: str, results: List):
        await self.set(query_key, results, CacheTier.QUERY)

    async def invalidate_org_cache(self, org_id: str):
        await self.delete_pattern(f"nexus:*:{org_id}:*")


redis_cache = RedisCache()


class CacheInvalidationService:
    """Service for managing cache invalidation patterns."""

    def __init__(self, cache: RedisCache):
        self.cache = cache

    async def on_entity_update(self, entity_type: str, entity_id: str, org_id: str):
        await self.cache.invalidate_entity(entity_type, entity_id)
        await self.cache.delete_pattern(f"nexus:query:{org_id}:{entity_type}*")

    async def on_entity_delete(self, entity_type: str, entity_id: str, org_id: str):
        await self.on_entity_update(entity_type, entity_id, org_id)

    async def on_user_login(self, user_id: str, org_id: str):
        await self.cache.delete_pattern(f"nexus:session:user:{user_id}*")

    async def on_org_settings_change(self, org_id: str):
        await self.cache.invalidate_org_cache(org_id)
