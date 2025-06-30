"""
Unit tests for Marcus Error Strategies

Tests retry policies, circuit breaker patterns, fallback mechanisms,
and error aggregation strategies.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.core.error_strategies import (
    RetryHandler, RetryConfig, RetryPolicy,
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState,
    FallbackHandler, ErrorAggregator,
    with_retry, with_circuit_breaker, with_fallback,
    ErrorStrategyRegistry, error_strategy_registry
)
from src.core.error_framework import (
    MarcusBaseError, TransientError, NetworkTimeoutError,
    IntegrationError, ErrorContext, ErrorSeverity, AuthorizationError
)


class TestRetryConfig:
    """Test suite for RetryConfig"""
    
    def test_retry_config_defaults(self):
        """Test RetryConfig with default values"""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.multiplier == 2.0
        assert config.jitter is True
        assert TransientError in config.retry_on
        assert IntegrationError in config.retry_on
    
    def test_retry_config_custom(self):
        """Test RetryConfig with custom values"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            multiplier=1.5,
            jitter=False
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.multiplier == 1.5
        assert config.jitter is False


class TestRetryHandler:
    """Test suite for RetryHandler"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = RetryConfig(max_attempts=3, base_delay=0.1, jitter=False)
        self.handler = RetryHandler(self.config)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("side_effect,expected_result,expected_calls,should_raise", [
        # Test successful operation that doesn't need retry
        (["success"], "success", 1, None),
        # Test retry behavior with transient error
        ([NetworkTimeoutError("test_service"), NetworkTimeoutError("test_service"), "success"], "success", 3, None),
        # Test no retry on non-retryable error
        ([AuthorizationError()], None, 1, AuthorizationError),
    ])
    async def test_retry_behavior(self, side_effect, expected_result, expected_calls, should_raise):
        """Test retry behavior with various scenarios"""
        mock_func = AsyncMock(side_effect=side_effect)
        
        if should_raise:
            with pytest.raises(should_raise):
                await self.handler.execute(mock_func)
        else:
            result = await self.handler.execute(mock_func)
            assert result == expected_result
        
        assert mock_func.call_count == expected_calls
    
    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test behavior when max attempts are exceeded"""
        mock_func = AsyncMock(side_effect=NetworkTimeoutError("test_service"))
        
        with pytest.raises(IntegrationError) as exc_info:
            await self.handler.execute(mock_func)
        
        assert mock_func.call_count == 3
        assert "Already retried 3 times" in exc_info.value.remediation.retry_strategy
    
    @pytest.mark.asyncio
    async def test_sync_function_execution(self):
        """Test executing synchronous function"""
        mock_func = Mock(return_value="sync_result")
        
        result = await self.handler.execute(mock_func)
        
        assert result == "sync_result"
        assert mock_func.call_count == 1
    
    def test_delay_calculation(self):
        """Test retry delay calculation"""
        # Test exponential backoff
        delay_0 = self.handler._calculate_delay(0)
        delay_1 = self.handler._calculate_delay(1)
        delay_2 = self.handler._calculate_delay(2)
        
        assert delay_0 == 0.1  # base_delay
        assert delay_1 == 0.2  # base_delay * multiplier
        assert delay_2 == 0.4  # base_delay * multiplier^2
    
    def test_delay_calculation_with_max(self):
        """Test delay calculation respects max_delay"""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, multiplier=2.0, jitter=False)
        handler = RetryHandler(config)
        
        delay_3 = handler._calculate_delay(3)  # Would be 80.0 without max
        
        assert delay_3 == 15.0  # Capped at max_delay
    
    def test_should_retry_logic(self):
        """Test retry decision logic"""
        transient_error = NetworkTimeoutError("test")
        auth_error = AuthorizationError()
        
        assert self.handler._should_retry(transient_error) is True
        assert self.handler._should_retry(auth_error) is False
    
    def test_should_stop_retry_logic(self):
        """Test stop retry decision logic"""
        transient_error = NetworkTimeoutError("test")
        auth_error = AuthorizationError()
        
        # Should stop on max attempts
        assert self.handler._should_stop_retry(transient_error, 2) is True  # attempt 2, max 3
        assert self.handler._should_stop_retry(transient_error, 1) is False  # attempt 1, max 3
        
        # Should stop on non-retryable error
        assert self.handler._should_stop_retry(auth_error, 0) is True


class TestCircuitBreakerConfig:
    """Test suite for CircuitBreakerConfig"""
    
    def test_circuit_breaker_config_defaults(self):
        """Test CircuitBreakerConfig default values"""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout == 60.0
        assert config.monitor_window == 300.0
        assert config.max_failures_per_window == 10


class TestCircuitBreaker:
    """Test suite for CircuitBreaker"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0,  # Short timeout for testing
            monitor_window=60.0
        )
        self.circuit_breaker = CircuitBreaker("test_service", self.config)
    
    @pytest.mark.asyncio
    async def test_successful_call_closed_state(self):
        """Test successful call in CLOSED state"""
        mock_func = AsyncMock(return_value="success")
        
        result = await self.circuit_breaker.call(mock_func)
        
        assert result == "success"
        assert self.circuit_breaker.state.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        """Test circuit opens after failure threshold"""
        mock_func = AsyncMock(side_effect=Exception("Service error"))
        
        # Fail enough times to open circuit
        for _ in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(mock_func)
        
        assert self.circuit_breaker.state.state == CircuitBreakerState.OPEN
        
        # Next call should be blocked
        with pytest.raises(IntegrationError) as exc_info:
            await self.circuit_breaker.call(mock_func)
        
        assert "circuit_breaker_open" in exc_info.value.operation
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_transition(self):
        """Test transition from OPEN to HALF_OPEN"""
        # Open the circuit
        mock_func = AsyncMock(side_effect=Exception("Service error"))
        for _ in range(self.config.failure_threshold):
            with pytest.raises(Exception):
                await self.circuit_breaker.call(mock_func)
        
        assert self.circuit_breaker.state.state == CircuitBreakerState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(1.1)  # Timeout is 1.0 seconds
        
        # Force state update
        async with self.circuit_breaker._lock:
            await self.circuit_breaker._update_state()
        
        assert self.circuit_breaker.state.state == CircuitBreakerState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_successes(self):
        """Test circuit closes after success threshold in HALF_OPEN"""
        # Manually set to HALF_OPEN state
        self.circuit_breaker.state.state = CircuitBreakerState.HALF_OPEN
        
        mock_func = AsyncMock(return_value="success")
        
        # Succeed enough times to close circuit
        for _ in range(self.config.success_threshold):
            result = await self.circuit_breaker.call(mock_func)
            assert result == "success"
        
        assert self.circuit_breaker.state.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_reopens_on_half_open_failure(self):
        """Test circuit reopens on failure during HALF_OPEN"""
        # Manually set to HALF_OPEN state
        self.circuit_breaker.state.state = CircuitBreakerState.HALF_OPEN
        
        mock_func = AsyncMock(side_effect=Exception("Still failing"))
        
        with pytest.raises(Exception):
            await self.circuit_breaker.call(mock_func)
        
        assert self.circuit_breaker.state.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_sync_function_call(self):
        """Test calling synchronous function through circuit breaker"""
        mock_func = Mock(return_value="sync_result")
        
        result = await self.circuit_breaker.call(mock_func)
        
        assert result == "sync_result"


class TestFallbackHandler:
    """Test suite for FallbackHandler"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = FallbackHandler("test_operation")
    
    @pytest.mark.asyncio
    async def test_primary_function_success(self):
        """Test successful primary function"""
        primary_func = AsyncMock(return_value="primary_result")
        
        result = await self.handler.execute_with_fallback(primary_func)
        
        assert result == "primary_result"
    
    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """Test fallback when primary function fails"""
        primary_func = AsyncMock(side_effect=Exception("Primary failed"))
        fallback_func = AsyncMock(return_value="fallback_result")
        
        self.handler.add_fallback(fallback_func, priority=1)
        
        result = await self.handler.execute_with_fallback(primary_func)
        
        assert result == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_multiple_fallbacks_priority(self):
        """Test multiple fallbacks with priority ordering"""
        primary_func = AsyncMock(side_effect=Exception("Primary failed"))
        fallback_1 = AsyncMock(side_effect=Exception("Fallback 1 failed"))
        fallback_2 = AsyncMock(return_value="fallback_2_result")
        fallback_3 = AsyncMock(return_value="fallback_3_result")
        
        # Add with different priorities
        self.handler.add_fallback(fallback_3, priority=3)
        self.handler.add_fallback(fallback_1, priority=1)
        self.handler.add_fallback(fallback_2, priority=2)
        
        result = await self.handler.execute_with_fallback(primary_func)
        
        # Should get result from fallback_2 (priority 2, first success)
        assert result == "fallback_2_result"
        assert fallback_1.called
        assert fallback_2.called
        assert not fallback_3.called  # Should not reach this
    
    @pytest.mark.asyncio
    async def test_cached_result_fallback(self):
        """Test using cached result as final fallback"""
        # Set up cache
        self.handler.cache["test_key"] = "cached_result"
        
        primary_func = AsyncMock(side_effect=Exception("Primary failed"))
        fallback_func = AsyncMock(side_effect=Exception("Fallback failed"))
        
        self.handler.add_fallback(fallback_func, priority=1)
        
        result = await self.handler.execute_with_fallback(
            primary_func,
            cache_key="test_key"
        )
        
        assert result == "cached_result"
    
    @pytest.mark.asyncio
    async def test_all_fallbacks_fail(self):
        """Test behavior when all fallbacks fail"""
        primary_func = AsyncMock(side_effect=Exception("Primary failed"))
        fallback_func = AsyncMock(side_effect=Exception("Fallback failed"))
        
        self.handler.add_fallback(fallback_func, priority=1)
        
        with pytest.raises(IntegrationError) as exc_info:
            await self.handler.execute_with_fallback(primary_func)
        
        assert "All fallback strategies exhausted" in exc_info.value.remediation.fallback_strategy
    
    @pytest.mark.asyncio
    async def test_sync_function_fallback(self):
        """Test fallback with synchronous functions"""
        primary_func = Mock(side_effect=Exception("Primary failed"))
        fallback_func = Mock(return_value="sync_fallback_result")
        
        self.handler.add_fallback(fallback_func, priority=1)
        
        result = await self.handler.execute_with_fallback(primary_func)
        
        assert result == "sync_fallback_result"


class TestErrorAggregator:
    """Test suite for ErrorAggregator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.aggregator = ErrorAggregator("batch_operation")
    
    def test_add_success(self):
        """Test adding successful operations"""
        self.aggregator.add_success()
        self.aggregator.add_success()
        
        assert self.aggregator.successes == 2
        assert self.aggregator.total_operations == 2
    
    def test_add_error_marcus_error(self):
        """Test adding Marcus error"""
        error = NetworkTimeoutError("test_service")
        
        self.aggregator.add_error(error, {"item_id": "123"})
        
        assert len(self.aggregator.errors) == 1
        assert self.aggregator.total_operations == 1
        assert self.aggregator.errors[0].context.custom_context["item_context"]["item_id"] == "123"
    
    def test_add_error_regular_exception(self):
        """Test adding regular exception"""
        error = ValueError("Regular error")
        
        self.aggregator.add_error(error, {"item_id": "456"})
        
        assert len(self.aggregator.errors) == 1
        assert self.aggregator.total_operations == 1
        assert isinstance(self.aggregator.errors[0], IntegrationError)
    
    def test_get_summary(self):
        """Test getting operation summary"""
        # Add successes and errors
        self.aggregator.add_success()
        self.aggregator.add_success()
        self.aggregator.add_error(NetworkTimeoutError("service1"))
        self.aggregator.add_error(NetworkTimeoutError("service2"))
        
        summary = self.aggregator.get_summary()
        
        assert summary["operation"] == "batch_operation"
        assert summary["total_operations"] == 4
        assert summary["successes"] == 2
        assert summary["errors"] == 2
        assert summary["success_rate"] == 0.5
        assert "NetworkTimeoutError" in summary["error_summary"]
        assert len(summary["error_summary"]["NetworkTimeoutError"]) == 2
    
    def test_has_errors(self):
        """Test error detection"""
        assert not self.aggregator.has_errors()
        
        self.aggregator.add_error(Exception("Test error"))
        
        assert self.aggregator.has_errors()
    
    def test_get_critical_errors(self):
        """Test getting critical errors"""
        
        # Add various severity errors
        self.aggregator.add_error(NetworkTimeoutError("service"))  # Medium severity
        self.aggregator.add_error(AuthorizationError())  # Critical severity
        
        critical_errors = self.aggregator.get_critical_errors()
        
        assert len(critical_errors) == 1
        assert critical_errors[0].severity == ErrorSeverity.CRITICAL
    
    def test_raise_if_critical(self):
        """Test raising on critical errors"""
        
        # No critical errors - should not raise
        self.aggregator.add_error(NetworkTimeoutError("service"))
        self.aggregator.raise_if_critical()  # Should not raise
        
        # Add critical error - should raise
        self.aggregator.add_error(AuthorizationError())
        
        with pytest.raises(AuthorizationError) as exc_info:
            self.aggregator.raise_if_critical()
        
        # Should have batch context
        assert "critical_errors_in_batch" in exc_info.value.context.custom_context


class TestDecorators:
    """Test suite for error handling decorators"""
    
    @pytest.mark.asyncio
    async def test_with_retry_decorator_async(self):
        """Test with_retry decorator on async function"""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01, jitter=False))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkTimeoutError("test_service")
            return "success"
        
        result = await failing_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_with_retry_decorator_sync(self):
        """Test with_retry decorator on sync function"""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=2, base_delay=0.01, jitter=False))
        def sync_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkTimeoutError("test_service")
            return "sync_success"
        
        result = sync_function()
        
        assert result == "sync_success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_with_circuit_breaker_decorator(self):
        """Test with_circuit_breaker decorator"""
        @with_circuit_breaker("test_service", CircuitBreakerConfig(failure_threshold=2))
        async def test_function():
            return "success"
        
        result = await test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_with_fallback_decorator(self):
        """Test with_fallback decorator"""
        async def fallback_func():
            return "fallback_result"
        
        @with_fallback(fallback_func)
        async def primary_func():
            raise Exception("Primary failed")
        
        result = await primary_func()
        assert result == "fallback_result"


class TestErrorStrategyRegistry:
    """Test suite for ErrorStrategyRegistry"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.registry = ErrorStrategyRegistry()
    
    def test_get_circuit_breaker(self):
        """Test getting circuit breaker from registry"""
        cb1 = self.registry.get_circuit_breaker("service1")
        cb2 = self.registry.get_circuit_breaker("service1")  # Same service
        cb3 = self.registry.get_circuit_breaker("service2")  # Different service
        
        assert cb1 is cb2  # Should return same instance
        assert cb1 is not cb3  # Different service, different instance
        assert cb1.name == "service1"
        assert cb3.name == "service2"
    
    def test_get_fallback_handler(self):
        """Test getting fallback handler from registry"""
        fh1 = self.registry.get_fallback_handler("operation1")
        fh2 = self.registry.get_fallback_handler("operation1")  # Same operation
        fh3 = self.registry.get_fallback_handler("operation2")  # Different operation
        
        assert fh1 is fh2  # Should return same instance
        assert fh1 is not fh3  # Different operation, different instance
    
    def test_retry_config_registration(self):
        """Test retry configuration registration and retrieval"""
        config = RetryConfig(max_attempts=5)
        
        self.registry.register_retry_config("special_operation", config)
        retrieved_config = self.registry.get_retry_config("special_operation")
        
        assert retrieved_config is config
        assert retrieved_config.max_attempts == 5
        
        # Test default for unregistered operation
        default_config = self.registry.get_retry_config("unknown_operation")
        assert isinstance(default_config, RetryConfig)
        assert default_config.max_attempts == 3  # Default value
    
    def test_health_status(self):
        """Test getting health status from registry"""
        # Create some circuit breakers
        cb1 = self.registry.get_circuit_breaker("service1")
        cb2 = self.registry.get_circuit_breaker("service2")
        
        health_status = self.registry.get_health_status()
        
        assert "service1" in health_status
        assert "service2" in health_status
        assert health_status["service1"]["state"] == "closed"
        assert health_status["service2"]["state"] == "closed"


class TestErrorStrategiesIntegration:
    """Integration tests for error strategies working together"""
    
    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker(self):
        """Test retry handler working with circuit breaker"""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.1)
        circuit_breaker = CircuitBreaker("integration_service", config)
        retry_handler = RetryHandler(RetryConfig(max_attempts=3, base_delay=0.01))
        
        # Function that always fails
        async def failing_function():
            raise NetworkTimeoutError("integration_service")
        
        # First, try with retry - should exhaust retries
        async def circuit_protected_call():
            return await circuit_breaker.call(failing_function)
            
        with pytest.raises(IntegrationError):
            await retry_handler.execute(circuit_protected_call)
        
        # Circuit should be open now
        assert circuit_breaker.state.state == CircuitBreakerState.OPEN
        
        # Direct call should be blocked
        with pytest.raises(IntegrationError) as exc_info:
            await circuit_breaker.call(failing_function)
        
        assert "circuit_breaker_open" in exc_info.value.operation
    
    @pytest.mark.asyncio
    async def test_fallback_with_retry(self):
        """Test fallback handler working with retry"""
        retry_config = RetryConfig(max_attempts=2, base_delay=0.01)
        fallback_handler = FallbackHandler("integration_test")
        
        async def primary_func():
            raise NetworkTimeoutError("primary_service")
        
        async def fallback_func():
            return "fallback_success"
        
        fallback_handler.add_fallback(fallback_func, priority=1)
        
        # Use retry within fallback
        async def primary_with_retry():
            return await RetryHandler(retry_config).execute(primary_func)
            
        result = await fallback_handler.execute_with_fallback(primary_with_retry)
        
        assert result == "fallback_success"