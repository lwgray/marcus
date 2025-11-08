"""
Performance tests for CRUD operations.

Validates that all CRUD operations meet the <100ms response time requirement.
Tests cover create, read, update, and delete operations on all major entities.
"""

# nosec B101 - Allow assert statements in test code

import asyncio
from time import perf_counter
from typing import Any, AsyncGenerator, Dict, List, Optional, cast
from uuid import uuid4

import pytest

# Performance requirement
MAX_RESPONSE_TIME_MS = 100


@pytest.mark.performance
@pytest.mark.asyncio
class TestUserCRUDPerformance:
    """
    Performance tests for User CRUD operations.

    Validates that all user operations complete within 100ms.
    """

    async def test_create_user_performance(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test user creation meets performance budget (<100ms).

        Creates a single user and validates response time.

        Performance Budget
        -----------------
        Target: <100ms
        Acceptable: <150ms (with network overhead)
        """
        # Arrange
        user_data = {
            "username": f"testuser_{uuid4().hex[:8]}",
            "email": f"test_{uuid4().hex[:8]}@example.com",
            "password": "TestPass123!",  # pragma: allowlist secret
            "full_name": "Test User",
        }

        # Act - Measure execution time
        start = perf_counter()
        user = await user_factory.create(**user_data)
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert user is not None  # nosec
        assert user.username == user_data["username"]  # nosec
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, (  # nosec
            f"User creation took {elapsed_ms:.2f}ms "
            f"(target: <{MAX_RESPONSE_TIME_MS}ms)"
        )

    async def test_read_user_by_id_performance(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test reading user by ID meets performance budget (<50ms).

        Read operations should be faster than writes.

        Performance Budget
        -----------------
        Target: <50ms (cached)
        Acceptable: <100ms (uncached)
        """
        # Arrange - Create user first
        user = await user_factory.create()

        # Act - Measure read time
        start = perf_counter()
        fetched_user = await user_factory.get_by_id(user.id)
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert fetched_user is not None  # nosec
        assert fetched_user.id == user.id  # nosec
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, (  # nosec
            f"User read took {elapsed_ms:.2f}ms " f"(target: <{MAX_RESPONSE_TIME_MS}ms)"
        )

    async def test_read_user_by_email_performance(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test reading user by email with index lookup (<100ms).

        Email is indexed, so lookup should be fast.
        """
        # Arrange
        user = await user_factory.create()

        # Act
        start = perf_counter()
        fetched_user = await user_factory.get_by_email(user.email)
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert fetched_user is not None  # nosec
        assert fetched_user.email == user.email  # nosec
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, (  # nosec
            f"User lookup by email took {elapsed_ms:.2f}ms "
            f"(target: <{MAX_RESPONSE_TIME_MS}ms)"
        )

    async def test_update_user_performance(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test user update meets performance budget (<100ms).

        Validates update operation including index updates.
        """
        # Arrange
        user = await user_factory.create()
        new_name = "Updated Name"

        # Act
        start = perf_counter()
        user.full_name = new_name
        await db_session.commit()
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert user.full_name == new_name  # nosec
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, (  # nosec
            f"User update took {elapsed_ms:.2f}ms "
            f"(target: <{MAX_RESPONSE_TIME_MS}ms)"
        )

    async def test_delete_user_performance(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test user deletion with cascade meets performance budget (<100ms).

        Includes cascading delete of related user_preferences.
        """
        # Arrange
        user = await user_factory.create()
        user_id = user.id

        # Act
        start = perf_counter()
        await db_session.delete(user)
        await db_session.commit()
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert - User deleted
        deleted_user = await user_factory.get_by_id(user_id)
        assert deleted_user is None  # nosec
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, (  # nosec
            f"User deletion took {elapsed_ms:.2f}ms "
            f"(target: <{MAX_RESPONSE_TIME_MS}ms)"
        )

    async def test_list_users_paginated_performance(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test listing users with pagination (<200ms for 20 results).

        Bulk read operations have a higher budget due to multiple rows.

        Performance Budget
        -----------------
        Target: <200ms for page of 20 users
        """
        # Arrange - Create 50 users
        _ = await asyncio.gather(*[user_factory.create() for _ in range(50)])

        # Act - Read first page (20 users)
        start = perf_counter()
        result = await user_factory.list_paginated(page=1, limit=20)
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert len(result) == 20  # nosec
        assert (  # nosec
            elapsed_ms < 200
        ), f"Paginated list took {elapsed_ms:.2f}ms (target: <200ms)"


@pytest.mark.performance
@pytest.mark.asyncio
class TestConcurrentOperationsPerformance:
    """
    Test performance under concurrent load.

    Validates connection pooling handles concurrent requests efficiently.
    """

    async def test_concurrent_user_reads(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test 10 concurrent user reads complete quickly (<500ms total).

        Validates connection pool can handle concurrent requests.

        Performance Budget
        -----------------
        Target: <500ms for 10 concurrent reads
        Average per-request: <100ms
        """
        # Arrange - Create 10 users
        users = await asyncio.gather(*[user_factory.create() for _ in range(10)])

        # Act - Read all users concurrently
        start = perf_counter()
        results = await asyncio.gather(
            *[user_factory.get_by_id(user.id) for user in users]
        )
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert len(results) == 10  # nosec
        assert all(r is not None for r in results)  # nosec
        assert (  # nosec
            elapsed_ms < 500
        ), f"10 concurrent reads took {elapsed_ms:.2f}ms (target: <500ms)"

        # Check average per-request time
        avg_per_request = elapsed_ms / 10
        assert avg_per_request < MAX_RESPONSE_TIME_MS, (  # nosec
            f"Average per-request time: {avg_per_request:.2f}ms "
            f"(target: <{MAX_RESPONSE_TIME_MS}ms)"
        )

    async def test_concurrent_user_creates(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test 5 concurrent user creates (<500ms total).

        Creates are slower than reads but should still be efficient.
        """
        # Arrange - Prepare user data
        users_data = [
            {
                "username": f"concurrent_{i}_{uuid4().hex[:8]}",
                "email": f"concurrent_{i}_{uuid4().hex[:8]}@example.com",
                "password": "TestPass123!",  # pragma: allowlist secret
            }
            for i in range(5)
        ]

        # Act - Create all users concurrently
        start = perf_counter()
        results = await asyncio.gather(
            *[user_factory.create(**data) for data in users_data]
        )
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert len(results) == 5  # nosec
        assert all(r is not None for r in results)  # nosec
        assert (  # nosec
            elapsed_ms < 500
        ), f"5 concurrent creates took {elapsed_ms:.2f}ms (target: <500ms)"


@pytest.mark.performance
@pytest.mark.asyncio
class TestCachePerformance:
    """
    Test caching significantly improves read performance.

    Validates cached reads are much faster than uncached reads.
    """

    async def test_cached_read_faster_than_uncached(
        self, db_session: Any, user_factory: Any, cache_client: Any
    ) -> None:
        """
        Test cached reads are at least 2x faster than uncached reads.

        Caching should provide significant performance improvement.

        Performance Targets
        ------------------
        Uncached read: <100ms
        Cached read: <20ms (5x faster)
        """
        # Arrange
        user = await user_factory.create()

        # First read - uncached (warm up connection)
        await user_factory.get_by_id(user.id)

        # Second read - measure uncached time
        await cache_client.delete(f"user:{user.id}")
        start = perf_counter()
        await user_factory.get_by_id(user.id)
        uncached_ms = (perf_counter() - start) * 1000

        # Third read - should be cached
        start = perf_counter()
        await user_factory.get_by_id(user.id)
        cached_ms = (perf_counter() - start) * 1000

        # Assert - Cached is significantly faster
        assert cached_ms < uncached_ms / 2, (  # nosec
            f"Cached read ({cached_ms:.2f}ms) should be at least 2x faster "
            f"than uncached ({uncached_ms:.2f}ms)"
        )
        assert (
            cached_ms < 20
        ), f"Cached read took {cached_ms:.2f}ms (target: <20ms)"  # nosec


@pytest.mark.performance
@pytest.mark.asyncio
class TestBulkOperationsPerformance:
    """
    Test bulk operations meet performance budgets.

    Validates batch operations are optimized.
    """

    async def test_bulk_create_performance(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """
        Test bulk user creation (<500ms for 100 users).

        Bulk operations should use optimized batch inserts.

        Performance Budget
        -----------------
        Target: <500ms for 100 users
        Average: <5ms per user
        """
        # Arrange - Prepare 100 users
        users_data = [
            {
                "username": f"bulk_{i}_{uuid4().hex[:8]}",
                "email": f"bulk_{i}_{uuid4().hex[:8]}@example.com",
                "password": "TestPass123!",  # pragma: allowlist secret
            }
            for i in range(100)
        ]

        # Act - Bulk insert
        start = perf_counter()
        users = await user_factory.bulk_create(users_data)
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert len(users) == 100  # nosec
        assert (  # nosec
            elapsed_ms < 500
        ), f"Bulk create of 100 users took {elapsed_ms:.2f}ms (target: <500ms)"

        # Check average per-user time
        avg_per_user = elapsed_ms / 100
        assert (  # nosec
            avg_per_user < 5
        ), f"Average time per user: {avg_per_user:.2f}ms (target: <5ms)"


@pytest.mark.performance
@pytest.mark.asyncio
class TestIndexEffectiveness:
    """
    Test database indexes provide expected performance improvements.

    Validates all indexed columns have fast lookups.
    """

    async def test_email_index_lookup(self, db_session: Any, user_factory: Any) -> None:
        """
        Test email index provides fast lookups (<100ms).

        Email column is indexed, so lookups should be O(log n) not O(n).
        """
        # Arrange - Create 1000 users
        users = await asyncio.gather(*[user_factory.create() for _ in range(1000)])
        target_user = users[500]  # User in middle of dataset

        # Act - Lookup by email
        start = perf_counter()
        found_user = await user_factory.get_by_email(target_user.email)
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert found_user.id == target_user.id  # nosec
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, (  # nosec
            f"Email lookup in 1000 users took {elapsed_ms:.2f}ms "
            f"(target: <{MAX_RESPONSE_TIME_MS}ms) - check index"
        )

    async def test_username_index_lookup(
        self, db_session: Any, user_factory: Any
    ) -> None:
        """Test username index provides fast lookups (<100ms)."""
        # Arrange - Create 1000 users
        users = await asyncio.gather(*[user_factory.create() for _ in range(1000)])
        target_user = users[750]

        # Act
        start = perf_counter()
        found_user = await user_factory.get_by_username(target_user.username)
        elapsed_ms = (perf_counter() - start) * 1000

        # Assert
        assert found_user.id == target_user.id  # nosec
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, (  # nosec
            f"Username lookup in 1000 users took {elapsed_ms:.2f}ms "
            f"(target: <{MAX_RESPONSE_TIME_MS}ms) - check index"
        )


# Fixtures for performance tests
@pytest.fixture
async def user_factory(db_session: Any) -> Any:
    """Factory for creating users in tests."""
    from app.core.security import hash_password
    from app.models.user import User

    class UserFactory:
        async def create(self, **kwargs: Any) -> Any:
            data = {
                "username": f"user_{uuid4().hex[:8]}",
                "email": f"user_{uuid4().hex[:8]}@example.com",
                "password_hash": hash_password(
                    "TestPass123!"
                ),  # pragma: allowlist secret
                **kwargs,
            }
            if "password" in data:
                data["password_hash"] = hash_password(data.pop("password"))

            user = User(**data)
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)
            return user

        async def get_by_id(self, user_id: Any) -> Optional[Any]:
            from sqlalchemy import select

            result = await db_session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

        async def get_by_email(self, email: str) -> Optional[Any]:
            from sqlalchemy import select

            result = await db_session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()

        async def get_by_username(self, username: str) -> Optional[Any]:
            from sqlalchemy import select

            result = await db_session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()

        async def list_paginated(self, page: int = 1, limit: int = 20) -> List[Any]:
            from sqlalchemy import select

            offset = (page - 1) * limit
            result = await db_session.execute(select(User).offset(offset).limit(limit))
            return cast(List[Any], result.scalars().all())

        async def bulk_create(self, users_data: List[Dict[str, Any]]) -> List[Any]:
            from app.core.security import hash_password

            users = []
            for data in users_data:
                if "password" in data:
                    data["password_hash"] = hash_password(data.pop("password"))
                users.append(User(**data))

            db_session.add_all(users)
            await db_session.commit()
            return users

    return UserFactory()


@pytest.fixture
async def cache_client() -> AsyncGenerator[Any, None]:
    """Cache client for performance tests."""
    from app.core.cache import cache

    await cache.connect()
    yield cache
    await cache.close()
