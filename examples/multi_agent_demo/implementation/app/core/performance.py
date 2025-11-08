"""
Performance monitoring and optimization utilities.

Provides tools to measure, monitor, and optimize query performance
to achieve <100ms response times for CRUD operations.
"""

import logging
from contextlib import asynccontextmanager
from functools import wraps
from time import perf_counter
from typing import Any, AsyncIterator, Callable, Optional, ParamSpec, TypeVar

# Type variables for generic decorators
P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


class PerformanceTimer:
    """
    Context manager for measuring execution time.

    Examples
    --------
    >>> with PerformanceTimer() as timer:
    ...     result = await expensive_operation()
    >>> print(f"Operation took {timer.elapsed_ms}ms")
    """

    def __init__(self, name: str = "operation"):
        """
        Initialize performance timer.

        Parameters
        ----------
        name : str
            Name of the operation being timed
        """
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed_ms: Optional[float] = None

    def __enter__(self) -> "PerformanceTimer":
        """Start timing."""
        self.start_time = perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop timing and calculate elapsed time."""
        self.end_time = perf_counter()
        if self.start_time is not None:
            self.elapsed_ms = (self.end_time - self.start_time) * 1000

        # Log slow operations (>100ms)
        if self.elapsed_ms is not None and self.elapsed_ms > 100:
            logger.warning(
                f"Slow operation detected: {self.name} took {self.elapsed_ms:.2f}ms "
                f"(target: <100ms)"
            )


@asynccontextmanager
async def async_performance_timer(
    name: str = "operation",
) -> AsyncIterator[dict[str, float]]:
    """
    Async context manager for measuring execution time.

    Parameters
    ----------
    name : str
        Name of the operation being timed

    Yields
    ------
    dict
        Dictionary to store timing results

    Examples
    --------
    >>> async with async_performance_timer("database_query") as timer:
    ...     result = await db.execute(query)
    >>> print(f"Query took {timer['elapsed_ms']}ms")
    """
    timer: dict[str, float] = {"start": perf_counter(), "elapsed_ms": 0}
    try:
        yield timer
    finally:
        timer["elapsed_ms"] = (perf_counter() - timer["start"]) * 1000

        # Log slow operations
        if timer["elapsed_ms"] > 100:
            logger.warning(
                f"Slow async operation: {name} took {timer['elapsed_ms']:.2f}ms "
                f"(target: <100ms)"
            )


def monitor_performance(
    threshold_ms: float = 100,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Monitor function performance and log warnings for slow operations.

    Logs warning if execution time exceeds threshold.

    Parameters
    ----------
    threshold_ms : float
        Performance threshold in milliseconds (default: 100)

    Returns
    -------
    Callable
        Decorated function with performance monitoring

    Examples
    --------
    >>> @monitor_performance(threshold_ms=100)
    >>> async def get_user(user_id: str):
    ...     return await db.query(User).filter(User.id == user_id).first()
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = perf_counter()
            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]
                return result  # type: ignore[no-any-return]
            finally:
                elapsed_ms = (perf_counter() - start) * 1000

                if elapsed_ms > threshold_ms:
                    logger.warning(
                        f"Performance threshold exceeded: {func.__name__} "
                        f"took {elapsed_ms:.2f}ms (threshold: {threshold_ms}ms)"
                    )
                else:
                    logger.debug(f"{func.__name__} completed in {elapsed_ms:.2f}ms")

        return wrapper  # type: ignore[return-value]

    return decorator


class QueryOptimizer:
    """
    Query optimization utilities and best practices.

    Provides helper methods for common query optimizations.
    """

    @staticmethod
    def build_pagination(page: int = 1, limit: int = 20) -> tuple[int, int]:
        """
        Calculate pagination offset and limit.

        Parameters
        ----------
        page : int
            Page number (1-indexed)
        limit : int
            Items per page (max: 100)

        Returns
        -------
        tuple[int, int]
            (offset, limit) for query

        Examples
        --------
        >>> offset, limit = QueryOptimizer.build_pagination(page=2, limit=20)
        >>> query = query.offset(offset).limit(limit)
        """
        # Enforce maximum limit to prevent performance issues
        limit = min(limit, 100)
        page = max(page, 1)
        offset = (page - 1) * limit
        return offset, limit

    @staticmethod
    def should_use_index_hint(table_size: int, filter_selectivity: float) -> bool:
        """
        Determine if query should use index hint.

        Parameters
        ----------
        table_size : int
            Approximate number of rows in table
        filter_selectivity : float
            Expected percentage of rows returned (0.0-1.0)

        Returns
        -------
        bool
            True if index hint recommended

        Notes
        -----
        Index hints are beneficial when:
        - Table has >10,000 rows
        - Filter selectivity is <20%
        """
        return table_size > 10000 and filter_selectivity < 0.2


class PerformanceMetrics:
    """
    Collect and report performance metrics.

    Tracks response times, cache hit rates, and query performance.
    """

    def __init__(self) -> None:
        """Initialize metrics storage."""
        self.query_times: list[float] = []
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.slow_queries: int = 0

    def record_query(self, elapsed_ms: float) -> None:
        """
        Record query execution time.

        Parameters
        ----------
        elapsed_ms : float
            Query execution time in milliseconds
        """
        self.query_times.append(elapsed_ms)
        if elapsed_ms > 100:
            self.slow_queries += 1

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        self.cache_misses += 1

    def get_summary(self) -> dict[str, float]:
        """
        Get performance metrics summary.

        Returns
        -------
        dict
            Performance statistics

        Examples
        --------
        >>> metrics = PerformanceMetrics()
        >>> summary = metrics.get_summary()
        >>> print(f"P95 latency: {summary['p95_ms']}ms")
        """
        if not self.query_times:
            return {
                "total_queries": 0,
                "avg_ms": 0,
                "min_ms": 0,
                "max_ms": 0,
                "p50_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "slow_queries": 0,
                "cache_hit_rate": 0,
            }

        sorted_times = sorted(self.query_times)
        total = len(sorted_times)

        cache_total = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / cache_total * 100 if cache_total > 0 else 0

        return {
            "total_queries": total,
            "avg_ms": sum(sorted_times) / total,
            "min_ms": sorted_times[0],
            "max_ms": sorted_times[-1],
            "p50_ms": sorted_times[int(total * 0.5)],
            "p95_ms": sorted_times[int(total * 0.95)],
            "p99_ms": sorted_times[int(total * 0.99)],
            "slow_queries": self.slow_queries,
            "cache_hit_rate": cache_hit_rate,
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.query_times.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.slow_queries = 0


# Global metrics instance
metrics = PerformanceMetrics()


class PerformanceBudget:
    """
    Enforce performance budgets for different operation types.

    Defines acceptable performance thresholds for various operations.
    """

    # CRUD operation budgets (in milliseconds)
    CREATE_BUDGET_MS = 100
    READ_BUDGET_MS = 50  # Read operations should be faster
    UPDATE_BUDGET_MS = 100
    DELETE_BUDGET_MS = 100

    # Bulk operation budgets
    BULK_CREATE_BUDGET_MS = 500  # Per batch
    BULK_READ_BUDGET_MS = 200  # Per page

    # Complex query budgets
    JOIN_QUERY_BUDGET_MS = 150
    AGGREGATION_BUDGET_MS = 200

    @classmethod
    def check_budget(cls, operation: str, elapsed_ms: float) -> bool:
        """
        Check if operation meets performance budget.

        Parameters
        ----------
        operation : str
            Operation type (create, read, update, delete)
        elapsed_ms : float
            Actual execution time in milliseconds

        Returns
        -------
        bool
            True if within budget, False otherwise

        Examples
        --------
        >>> is_ok = PerformanceBudget.check_budget("read", 45)
        >>> if not is_ok:
        ...     logger.warning("Read operation exceeded budget")
        """
        budgets = {
            "create": cls.CREATE_BUDGET_MS,
            "read": cls.READ_BUDGET_MS,
            "update": cls.UPDATE_BUDGET_MS,
            "delete": cls.DELETE_BUDGET_MS,
            "bulk_create": cls.BULK_CREATE_BUDGET_MS,
            "bulk_read": cls.BULK_READ_BUDGET_MS,
            "join": cls.JOIN_QUERY_BUDGET_MS,
            "aggregation": cls.AGGREGATION_BUDGET_MS,
        }

        budget = budgets.get(operation, 100)
        return elapsed_ms <= budget


class QueryAnalyzer:
    """
    Analyze query plans and suggest optimizations.

    Provides tools to understand query performance and identify bottlenecks.
    """

    @staticmethod
    async def explain_query(session: Any, query: Any) -> dict[str, Any]:
        """
        Get query execution plan (EXPLAIN ANALYZE).

        Parameters
        ----------
        session : AsyncSession
            Database session
        query : Select
            SQLAlchemy query to analyze

        Returns
        -------
        dict
            Query execution plan details

        Examples
        --------
        >>> from sqlalchemy import select
        >>> query = select(User).where(User.email == email)
        >>> plan = await QueryAnalyzer.explain_query(db, query)
        >>> print(plan["execution_time_ms"])
        """
        # Convert query to SQL
        compiled = query.compile(compile_kwargs={"literal_binds": True})
        sql = str(compiled)

        # Execute EXPLAIN ANALYZE
        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
        result = await session.execute(explain_sql)
        plan = result.scalar()

        return {
            "plan": plan,
            "execution_time_ms": plan[0]["Execution Time"] if plan else 0,
        }
