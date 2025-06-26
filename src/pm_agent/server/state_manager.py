"""
State management and persistence layer for Marcus.

This module provides a scalable state management solution with
support for Redis, PostgreSQL, and distributed caching.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Any, List, Set
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from enum import Enum

import redis.asyncio as redis
from sqlalchemy import create_engine, Column, String, JSON, DateTime, Integer, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from cachetools import TTLCache
import pickle

from pm_agent.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class CacheLevel(Enum):
    """Cache levels for multi-tier caching."""
    LOCAL = "local"
    REDIS = "redis"
    DATABASE = "database"


# Database Models
class AgentModel(Base):
    """Agent database model."""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    capabilities = Column(JSON, default={})
    status = Column(String, default="idle")
    current_task_id = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_agent_status', 'status'),
        Index('idx_agent_heartbeat', 'last_heartbeat'),
    )


class TaskModel(Base):
    """Task database model."""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, default="pending")
    priority = Column(Integer, default=0)
    assigned_agent_id = Column(String, nullable=True)
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    metadata = Column(JSON, default={})
    
    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_agent', 'assigned_agent_id'),
        Index('idx_task_priority', 'priority'),
    )


class ProjectStateModel(Base):
    """Project state database model."""
    __tablename__ = "project_states"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    state = Column(JSON, default={})
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StateManager:
    """
    Manages application state with multi-tier caching and persistence.
    
    Features:
    - Local in-memory cache (L1)
    - Redis distributed cache (L2)
    - PostgreSQL persistent storage (L3)
    - Automatic cache invalidation
    - Optimistic locking for concurrent updates
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        db_engine: Optional[Any] = None,
        local_cache_size: int = 1000,
        local_cache_ttl: int = 60,  # 1 minute
        redis_ttl: int = 300  # 5 minutes
    ):
        # Cache layers
        self.local_cache = TTLCache(maxsize=local_cache_size, ttl=local_cache_ttl)
        self.redis = redis_client
        self.db_engine = db_engine
        self.db_session_maker = None
        
        # Cache configuration
        self.redis_ttl = redis_ttl
        
        # Metrics
        self.cache_hits = {"local": 0, "redis": 0, "database": 0}
        self.cache_misses = 0
        
        if db_engine:
            self.db_session_maker = async_sessionmaker(
                db_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
    
    async def initialize(self):
        """Initialize the state manager."""
        if self.db_engine:
            # Create tables if they don't exist
            async with self.db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized")
    
    # Agent Management
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent data with multi-tier caching."""
        cache_key = f"agent:{agent_id}"
        
        # Check L1 cache (local)
        if cache_key in self.local_cache:
            self.cache_hits["local"] += 1
            return self.local_cache[cache_key]
        
        # Check L2 cache (Redis)
        if self.redis:
            data = await self.redis.get(cache_key)
            if data:
                self.cache_hits["redis"] += 1
                agent_data = json.loads(data)
                self.local_cache[cache_key] = agent_data
                return agent_data
        
        # Check L3 (Database)
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                result = await session.get(AgentModel, agent_id)
                if result:
                    self.cache_hits["database"] += 1
                    agent_data = {
                        "id": result.id,
                        "name": result.name,
                        "capabilities": result.capabilities,
                        "status": result.status,
                        "current_task_id": result.current_task_id,
                        "last_heartbeat": result.last_heartbeat.isoformat() if result.last_heartbeat else None
                    }
                    
                    # Populate caches
                    await self._populate_caches(cache_key, agent_data)
                    return agent_data
        
        self.cache_misses += 1
        return None
    
    async def set_agent(self, agent_id: str, agent_data: Dict[str, Any]):
        """Set agent data with write-through caching."""
        cache_key = f"agent:{agent_id}"
        
        # Update database first (write-through)
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                agent = await session.get(AgentModel, agent_id)
                if not agent:
                    agent = AgentModel(id=agent_id)
                    session.add(agent)
                
                # Update fields
                agent.name = agent_data.get("name", agent.name)
                agent.capabilities = agent_data.get("capabilities", agent.capabilities)
                agent.status = agent_data.get("status", agent.status)
                agent.current_task_id = agent_data.get("current_task_id")
                agent.last_heartbeat = datetime.utcnow()
                
                await session.commit()
        
        # Update caches
        await self._populate_caches(cache_key, agent_data)
    
    async def update_agent_heartbeat(self, agent_id: str):
        """Update agent heartbeat timestamp."""
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                agent = await session.get(AgentModel, agent_id)
                if agent:
                    agent.last_heartbeat = datetime.utcnow()
                    await session.commit()
        
        # Invalidate caches
        await self._invalidate_cache(f"agent:{agent_id}")
    
    async def get_active_agents(self, since_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get agents that have been active recently."""
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                cutoff_time = datetime.utcnow() - timedelta(minutes=since_minutes)
                query = session.query(AgentModel).filter(
                    AgentModel.last_heartbeat >= cutoff_time
                )
                results = await session.execute(query)
                agents = results.scalars().all()
                
                return [{
                    "id": agent.id,
                    "name": agent.name,
                    "status": agent.status,
                    "current_task_id": agent.current_task_id,
                    "last_heartbeat": agent.last_heartbeat.isoformat()
                } for agent in agents]
        
        return []
    
    # Task Management
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task data with caching."""
        cache_key = f"task:{task_id}"
        
        # Check caches
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Check database
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                result = await session.get(TaskModel, task_id)
                if result:
                    task_data = {
                        "id": result.id,
                        "title": result.title,
                        "description": result.description,
                        "status": result.status,
                        "priority": result.priority,
                        "assigned_agent_id": result.assigned_agent_id,
                        "progress": result.progress,
                        "metadata": result.metadata
                    }
                    
                    await self._populate_caches(cache_key, task_data)
                    return task_data
        
        return None
    
    async def set_task(self, task_id: str, task_data: Dict[str, Any]):
        """Set task data."""
        cache_key = f"task:{task_id}"
        
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                task = await session.get(TaskModel, task_id)
                if not task:
                    task = TaskModel(id=task_id)
                    session.add(task)
                
                # Update fields
                for field in ["title", "description", "status", "priority", 
                             "assigned_agent_id", "progress", "metadata"]:
                    if field in task_data:
                        setattr(task, field, task_data[field])
                
                if task_data.get("status") == "completed":
                    task.completed_at = datetime.utcnow()
                
                await session.commit()
        
        await self._populate_caches(cache_key, task_data)
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending tasks ordered by priority."""
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                query = session.query(TaskModel).filter(
                    TaskModel.status == "pending"
                ).order_by(
                    TaskModel.priority.desc(),
                    TaskModel.created_at
                ).limit(limit)
                
                results = await session.execute(query)
                tasks = results.scalars().all()
                
                return [{
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "priority": task.priority,
                    "metadata": task.metadata
                } for task in tasks]
        
        return []
    
    # Project State Management
    async def get_project_state(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project state with versioning."""
        cache_key = f"project:{project_id}"
        
        # Check caches
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Check database
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                result = await session.get(ProjectStateModel, project_id)
                if result:
                    project_data = {
                        "id": result.id,
                        "name": result.name,
                        "state": result.state,
                        "version": result.version
                    }
                    
                    await self._populate_caches(cache_key, project_data)
                    return project_data
        
        return None
    
    async def set_project_state(self, project_id: str, state: Dict[str, Any], 
                               expected_version: Optional[int] = None):
        """Set project state with optimistic locking."""
        cache_key = f"project:{project_id}"
        
        if self.db_session_maker:
            async with self.db_session_maker() as session:
                project = await session.get(ProjectStateModel, project_id)
                
                if not project:
                    project = ProjectStateModel(
                        id=project_id,
                        name=state.get("name", project_id)
                    )
                    session.add(project)
                else:
                    # Check version for optimistic locking
                    if expected_version is not None and project.version != expected_version:
                        raise ValueError(f"Version mismatch. Expected {expected_version}, got {project.version}")
                
                project.state = state
                project.version += 1
                
                await session.commit()
                
                # Return new version
                new_version = project.version
        
        await self._invalidate_cache(cache_key)
        return new_version
    
    # Cache Management
    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache hierarchy."""
        # Check local cache
        if key in self.local_cache:
            self.cache_hits["local"] += 1
            return self.local_cache[key]
        
        # Check Redis
        if self.redis:
            data = await self.redis.get(key)
            if data:
                self.cache_hits["redis"] += 1
                result = json.loads(data)
                self.local_cache[key] = result
                return result
        
        return None
    
    async def _populate_caches(self, key: str, data: Dict[str, Any]):
        """Populate all cache layers."""
        # Update local cache
        self.local_cache[key] = data
        
        # Update Redis
        if self.redis:
            await self.redis.set(
                key,
                json.dumps(data, default=str),
                ex=self.redis_ttl
            )
    
    async def _invalidate_cache(self, key: str):
        """Invalidate cache entry across all layers."""
        # Remove from local cache
        self.local_cache.pop(key, None)
        
        # Remove from Redis
        if self.redis:
            await self.redis.delete(key)
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all cache entries matching a pattern."""
        # Clear matching entries from local cache
        keys_to_remove = [k for k in self.local_cache.keys() if pattern in k]
        for key in keys_to_remove:
            del self.local_cache[key]
        
        # Clear from Redis
        if self.redis:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=f"*{pattern}*", count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
    
    # Bulk Operations
    async def get_agents_batch(self, agent_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get multiple agents efficiently."""
        results = {}
        missing_ids = []
        
        # Check caches first
        for agent_id in agent_ids:
            agent_data = await self._get_from_cache(f"agent:{agent_id}")
            if agent_data:
                results[agent_id] = agent_data
            else:
                missing_ids.append(agent_id)
        
        # Fetch missing from database
        if missing_ids and self.db_session_maker:
            async with self.db_session_maker() as session:
                query = session.query(AgentModel).filter(
                    AgentModel.id.in_(missing_ids)
                )
                db_results = await session.execute(query)
                agents = db_results.scalars().all()
                
                for agent in agents:
                    agent_data = {
                        "id": agent.id,
                        "name": agent.name,
                        "capabilities": agent.capabilities,
                        "status": agent.status,
                        "current_task_id": agent.current_task_id
                    }
                    results[agent.id] = agent_data
                    await self._populate_caches(f"agent:{agent.id}", agent_data)
        
        return results
    
    # Statistics
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(self.cache_hits.values())
        total_requests = total_hits + self.cache_misses
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": (total_hits / total_requests * 100) if total_requests > 0 else 0,
            "local_cache_size": len(self.local_cache),
            "local_cache_max_size": self.local_cache.maxsize
        }
    
    # Cleanup
    async def cleanup_stale_data(self, days: int = 30):
        """Clean up old data from the database."""
        if self.db_session_maker:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            async with self.db_session_maker() as session:
                # Delete old completed tasks
                await session.execute(
                    TaskModel.__table__.delete().where(
                        (TaskModel.status == "completed") &
                        (TaskModel.completed_at < cutoff_date)
                    )
                )
                
                # Delete inactive agents
                await session.execute(
                    AgentModel.__table__.delete().where(
                        AgentModel.last_heartbeat < cutoff_date
                    )
                )
                
                await session.commit()
                logger.info(f"Cleaned up data older than {days} days")


# Example distributed lock implementation
class DistributedLock:
    """Redis-based distributed lock for coordinating multiple instances."""
    
    def __init__(self, redis_client: redis.Redis, key: str, timeout: int = 10):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.token = None
    
    async def __aenter__(self):
        """Acquire the lock."""
        import uuid
        self.token = str(uuid.uuid4())
        
        while True:
            # Try to acquire lock
            acquired = await self.redis.set(
                self.key,
                self.token,
                nx=True,  # Only set if not exists
                ex=self.timeout
            )
            
            if acquired:
                return self
            
            # Wait before retrying
            await asyncio.sleep(0.1)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        if self.token:
            # Only delete if we own the lock
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await self.redis.eval(lua_script, 1, self.key, self.token)


# Example usage
async def example_usage():
    """Example of using the state manager."""
    # Initialize components
    redis_client = await redis.from_url("redis://localhost:6379")
    db_engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/pmagent")
    
    state_manager = StateManager(
        redis_client=redis_client,
        db_engine=db_engine
    )
    await state_manager.initialize()
    
    # Example: Managing agent state
    await state_manager.set_agent("agent-1", {
        "name": "Worker Agent 1",
        "capabilities": {"python": True, "nodejs": True},
        "status": "idle"
    })
    
    # Example: Using distributed lock
    async with DistributedLock(redis_client, "task-assignment"):
        # Critical section - only one instance can assign tasks
        pending_tasks = await state_manager.get_pending_tasks()
        if pending_tasks:
            task = pending_tasks[0]
            await state_manager.set_task(task["id"], {
                "status": "assigned",
                "assigned_agent_id": "agent-1"
            })
    
    # Get cache statistics
    stats = state_manager.get_cache_stats()
    print(f"Cache stats: {stats}")
    
    # Cleanup
    await redis_client.close()
    await db_engine.dispose()


if __name__ == "__main__":
    asyncio.run(example_usage())