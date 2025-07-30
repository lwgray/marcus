# Progressive Architecture Implementation Guide

This guide shows exactly how to build Marcus with a simple start but enterprise-ready architecture.

## 🏗️ Core Design Principles

1. **Zero Config Start**: Works instantly for solo devs
2. **Auto-Detection**: Automatically uses better infrastructure when available
3. **Graceful Fallbacks**: Never breaks when scaling features missing
4. **Progressive Enhancement**: Features unlock as infrastructure improves

## 📦 Implementation Patterns

### 1. Storage Layer Abstraction

```python
# src/storage/__init__.py
import os
from abc import ABC, abstractmethod
from typing import Optional

class StorageBackend(ABC):
    """Abstract base for all storage backends"""

    @abstractmethod
    async def initialize(self):
        """Set up the storage backend"""
        pass

    @abstractmethod
    async def get(self, collection: str, id: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def set(self, collection: str, id: str, data: dict):
        pass

    @abstractmethod
    async def query(self, collection: str, filter: dict) -> list:
        pass

    @abstractmethod
    async def delete(self, collection: str, id: str):
        pass

# src/storage/sqlite_backend.py
import sqlite3
import json
import aiosqlite
from pathlib import Path

class SQLiteBackend(StorageBackend):
    """Default storage - zero configuration required"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / ".marcus" / "marcus.db")

    async def initialize(self):
        """Create tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS storage (
                    collection TEXT,
                    id TEXT,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (collection, id)
                )
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_collection
                ON storage(collection)
            ''')
            await db.commit()

    async def get(self, collection: str, id: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data FROM storage WHERE collection = ? AND id = ?",
                (collection, id)
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else None

    async def set(self, collection: str, id: str, data: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO storage (collection, id, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (collection, id, json.dumps(data)))
            await db.commit()

# src/storage/postgres_backend.py
import asyncpg
import json
from typing import Optional

class PostgreSQLBackend(StorageBackend):
    """Team storage - concurrent access support"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None

    async def initialize(self):
        """Create connection pool and tables"""
        self.pool = await asyncpg.create_pool(self.connection_string)

        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS storage (
                    collection TEXT,
                    id TEXT,
                    data JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (collection, id)
                )
            ''')
            # Create indexes for performance
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_collection
                ON storage(collection)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_data_gin
                ON storage USING gin(data)
            ''')

    async def get(self, collection: str, id: str) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM storage WHERE collection = $1 AND id = $2",
                collection, id
            )
            return dict(row['data']) if row else None

# src/storage/factory.py
def get_storage_backend() -> StorageBackend:
    """Auto-detect best available storage"""

    # Check environment first
    if db_url := os.getenv('DATABASE_URL'):
        if db_url.startswith('postgresql://'):
            from .postgres_backend import PostgreSQLBackend
            return PostgreSQLBackend(db_url)
        elif db_url.startswith('mongodb://'):
            from .mongo_backend import MongoDBBackend
            return MongoDBBackend(db_url)

    # Default to SQLite for zero config
    from .sqlite_backend import SQLiteBackend
    return SQLiteBackend()

# Usage in main app
storage = get_storage_backend()
await storage.initialize()
```

### 2. Progressive Caching Strategy

```python
# src/cache/__init__.py
from abc import ABC, abstractmethod
from typing import Optional, Any
import time

class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300):
        pass

    @abstractmethod
    async def delete(self, key: str):
        pass

    @abstractmethod
    async def clear(self):
        pass

# src/cache/memory_cache.py
from collections import OrderedDict
from datetime import datetime, timedelta

class MemoryCache(CacheBackend):
    """Simple in-memory cache for solo developers"""

    def __init__(self, max_size: int = 1000):
        self.cache = OrderedDict()
        self.max_size = max_size

    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, expires = self.cache[key]
            if expires > datetime.now():
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        expires = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = (value, expires)

        # Enforce max size (LRU eviction)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

# src/cache/redis_cache.py
import json
import redis.asyncio as redis
from typing import Optional, Any

class RedisCache(CacheBackend):
    """Distributed cache for teams"""

    def __init__(self, url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(url)

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: int = 300):
        await self.redis.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )

    async def delete(self, key: str):
        await self.redis.delete(key)

# src/cache/manager.py
class CacheManager:
    """Manages multiple cache layers with fallback"""

    def __init__(self):
        self.layers = []
        self._initialize_layers()

    def _initialize_layers(self):
        """Add cache layers based on availability"""

        # Try Redis first (for teams)
        if redis_url := os.getenv('REDIS_URL'):
            try:
                from .redis_cache import RedisCache
                self.layers.append(RedisCache(redis_url))
                print("✓ Redis cache enabled")
            except Exception as e:
                print(f"Redis unavailable, using memory cache: {e}")

        # Always have memory cache as fallback
        from .memory_cache import MemoryCache
        self.layers.append(MemoryCache())

    async def get(self, key: str) -> Optional[Any]:
        """Try each cache layer in order"""
        for cache in self.layers:
            try:
                if value := await cache.get(key):
                    # Populate higher layers
                    for higher_cache in self.layers[:self.layers.index(cache)]:
                        await higher_cache.set(key, value)
                    return value
            except Exception:
                continue  # Try next layer
        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set in all available cache layers"""
        for cache in self.layers:
            try:
                await cache.set(key, value, ttl)
            except Exception:
                continue  # Best effort

# Usage
cache = CacheManager()  # Auto-detects best setup
value = await cache.get("project:123:status")
```

### 3. Real-time Updates (Progressive Enhancement)

```python
# src/realtime/__init__.py
from abc import ABC, abstractmethod
from typing import Dict, List, Callable

class RealtimeBackend(ABC):
    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable):
        pass

    @abstractmethod
    async def publish(self, channel: str, data: dict):
        pass

# src/realtime/polling_backend.py
import asyncio
from collections import defaultdict

class PollingBackend(RealtimeBackend):
    """Fallback for solo developers - simple polling"""

    def __init__(self):
        self.subscribers = defaultdict(list)
        self.messages = defaultdict(list)

    async def subscribe(self, channel: str, callback: Callable):
        self.subscribers[channel].append(callback)

    async def publish(self, channel: str, data: dict):
        # Store for polling
        self.messages[channel].append(data)

        # Direct callback for local subscribers
        for callback in self.subscribers[channel]:
            await callback(data)

    async def get_updates(self, channel: str, since: float) -> List[dict]:
        """For HTTP polling from frontend"""
        return [
            msg for msg in self.messages[channel]
            if msg.get('timestamp', 0) > since
        ]

# src/realtime/websocket_backend.py
from typing import Set
import asyncio
import websockets
import json

class WebSocketBackend(RealtimeBackend):
    """Real-time updates for teams"""

    def __init__(self):
        self.connections: Set[websockets.WebSocketServerProtocol] = set()
        self.channels = defaultdict(set)

    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        self.connections.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'subscribe':
                    self.channels[data['channel']].add(websocket)
        finally:
            self.connections.remove(websocket)
            for channel_subs in self.channels.values():
                channel_subs.discard(websocket)

    async def publish(self, channel: str, data: dict):
        """Send to all subscribers"""
        message = json.dumps({
            'channel': channel,
            'data': data,
            'timestamp': time.time()
        })

        # Send to WebSocket subscribers
        for ws in self.channels[channel]:
            try:
                await ws.send(message)
            except:
                pass  # Client disconnected

# src/realtime/manager.py
class RealtimeManager:
    """Auto-selects best realtime backend"""

    def __init__(self):
        self.backend = self._select_backend()

    def _select_backend(self):
        # Check if Redis is available for teams
        if os.getenv('REDIS_URL'):
            try:
                from .redis_pubsub import RedisPubSubBackend
                return RedisPubSubBackend()
            except:
                pass

        # Check if we should enable WebSockets
        if os.getenv('ENABLE_WEBSOCKETS'):
            from .websocket_backend import WebSocketBackend
            return WebSocketBackend()

        # Default to polling for solo devs
        from .polling_backend import PollingBackend
        return PollingBackend()

    async def publish_update(self, update_type: str, data: dict):
        """Publish update through best available channel"""
        await self.backend.publish(f"updates:{update_type}", {
            'type': update_type,
            'data': data,
            'timestamp': time.time()
        })
```

### 4. Feature Detection and Progressive UI

```python
# src/features.py
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Features:
    """Feature flags based on infrastructure"""

    # Infrastructure detection
    has_redis: bool = False
    has_postgres: bool = False
    has_websockets: bool = False
    has_kubernetes: bool = False

    # User context
    user_count: int = 1
    project_count: int = 1
    storage_size_mb: float = 0

    # Plan/tier
    tier: str = "solo"  # solo, team, enterprise

    @classmethod
    async def detect(cls) -> 'Features':
        """Auto-detect available features"""
        features = cls()

        # Check Redis
        if redis_url := os.getenv('REDIS_URL'):
            try:
                import redis
                r = redis.from_url(redis_url)
                r.ping()
                features.has_redis = True
            except:
                pass

        # Check database
        if db_url := os.getenv('DATABASE_URL'):
            features.has_postgres = 'postgresql://' in db_url

        # Check container orchestration
        features.has_kubernetes = os.path.exists('/var/run/secrets/kubernetes.io')

        # Get usage stats
        storage = get_storage_backend()
        features.user_count = await storage.count('users')
        features.project_count = await storage.count('projects')

        # Determine tier
        if features.has_kubernetes:
            features.tier = "enterprise"
        elif features.has_postgres and features.has_redis:
            features.tier = "team"
        else:
            features.tier = "solo"

        return features

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for frontend"""
        return {
            'tier': self.tier,
            'capabilities': {
                'realtime': self.has_redis or self.has_websockets,
                'collaboration': self.has_postgres,
                'advanced_analytics': self.tier in ['team', 'enterprise'],
                'unlimited_projects': self.tier != 'solo',
                'api_access': True,
                'webhooks': self.tier in ['team', 'enterprise'],
                'sso': self.tier == 'enterprise',
                'audit_logs': self.tier == 'enterprise'
            }
        }

# API endpoint for frontend
@app.route('/api/features')
async def get_features():
    features = await Features.detect()
    return jsonify(features.to_dict())
```

### 5. Frontend Progressive Enhancement

```jsx
// src/hooks/useFeatures.js
import { useState, useEffect } from 'react';

export function useFeatures() {
  const [features, setFeatures] = useState({
    tier: 'solo',
    capabilities: {
      realtime: false,
      collaboration: false,
      advanced_analytics: false
    }
  });

  useEffect(() => {
    fetch('/api/features')
      .then(res => res.json())
      .then(setFeatures);
  }, []);

  return features;
}

// src/components/Dashboard.jsx
function Dashboard() {
  const features = useFeatures();

  return (
    <div>
      <h1>Marcus Dashboard</h1>

      {/* Always show basic features */}
      <ProjectHealth />
      <TaskQueue />

      {/* Progressive enhancement */}
      {features.capabilities.realtime ? (
        <RealtimeUpdates />
      ) : (
        <RefreshButton />
      )}

      {features.capabilities.collaboration && (
        <TeamView />
      )}

      {features.capabilities.advanced_analytics && (
        <PredictiveAnalytics />
      )}

      {/* Upgrade prompts */}
      {features.tier === 'solo' && (
        <UpgradePrompt
          message="Want real-time updates? Add Redis to your setup!"
          docsLink="/docs/scaling/adding-redis"
        />
      )}
    </div>
  );
}
```

### 6. Migration Utilities

```python
# src/migrations/manager.py
class MigrationManager:
    """Handles data migrations between storage backends"""

    async def migrate_sqlite_to_postgres(self, sqlite_path: str, postgres_url: str):
        """Migrate from SQLite to PostgreSQL"""
        from storage.sqlite_backend import SQLiteBackend
        from storage.postgres_backend import PostgreSQLBackend

        print("Starting migration from SQLite to PostgreSQL...")

        # Initialize both backends
        source = SQLiteBackend(sqlite_path)
        target = PostgreSQLBackend(postgres_url)
        await source.initialize()
        await target.initialize()

        # Get all collections
        collections = await source.list_collections()

        for collection in collections:
            print(f"Migrating collection: {collection}")

            # Stream data to handle large datasets
            async for batch in source.stream_all(collection, batch_size=1000):
                await target.bulk_insert(collection, batch)
                print(f"  Migrated {len(batch)} records")

        print("Migration complete!")

        # Verify data integrity
        for collection in collections:
            source_count = await source.count(collection)
            target_count = await target.count(collection)
            assert source_count == target_count, f"Count mismatch in {collection}"

        print("Data integrity verified ✓")

# CLI command
@click.command()
@click.option('--from', 'source', required=True)
@click.option('--to', 'target', required=True)
async def migrate(source, target):
    """Migrate data between storage backends"""
    manager = MigrationManager()

    if source == 'sqlite' and target == 'postgres':
        await manager.migrate_sqlite_to_postgres(
            sqlite_path=get_sqlite_path(),
            postgres_url=os.getenv('DATABASE_URL')
        )
```

## 🚀 Implementation Checklist

### Phase 1: MVP (Solo Developer)
- [ ] Implement SQLite storage backend
- [ ] Add simple memory cache
- [ ] Create basic dashboard with manual refresh
- [ ] Ensure 5-minute setup experience
- [ ] Write solo developer quickstart

### Phase 2: Team Features
- [ ] Add PostgreSQL backend with auto-detection
- [ ] Implement Redis cache layer
- [ ] Add WebSocket support for real-time
- [ ] Build migration tool (SQLite → PostgreSQL)
- [ ] Create team setup guide

### Phase 3: Scale Features
- [ ] Add background job processing
- [ ] Implement advanced caching strategies
- [ ] Add monitoring and metrics
- [ ] Create Kubernetes manifests
- [ ] Write scaling documentation

### Phase 4: Enterprise
- [ ] Multi-tenancy support
- [ ] SSO/SAML integration
- [ ] Audit logging
- [ ] Advanced security features
- [ ] Enterprise setup guide

## 🎯 Key Takeaways

1. **Start Simple**: SQLite + memory cache = instant value
2. **Auto-Detect**: System discovers and uses better infrastructure
3. **Never Break**: Graceful fallbacks at every level
4. **Progressive UI**: Features appear as infrastructure improves
5. **Easy Migration**: One command to level up

This architecture ensures Marcus can serve everyone from solo hackers to Fortune 500 companies, with a smooth growth path between each stage.
