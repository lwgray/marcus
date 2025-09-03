"""
Unit tests for resilience patterns and security fixes.
"""
import asyncio
import secrets
import time
from unittest.mock import AsyncMock, Mock, patch
import pytest
from src.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    GracefulDegradation,
    RetryConfig,
    with_circuit_breaker,
    with_fallback,
    with_retry,
)


class TestRetryConfigSecurity:
    """Test security improvements in retry logic"""

    @patch('src.core.resilience.secrets.SystemRandom')
    def test_retry_uses_secure_random_for_jitter(self, mock_system_random):
        """Test that retry logic uses cryptographically secure random for jitter"""
        mock_random_instance = Mock()
        mock_random_instance.random.return_value = 0.5
        mock_system_random.return_value = mock_random_instance
        
        config = RetryConfig(max_attempts=2, base_delay=1.0, jitter=True)
        
        @with_retry(config)
        def failing_function():
            raise ValueError("Test error")
        
        # This should fail after 2 attempts
        with pytest.raises(ValueError):
            failing_function()
        
        # Verify SystemRandom was used
        mock_system_random.assert_called()
        mock_random_instance.random.assert_called()

    @patch('src.core.resilience.secrets.SystemRandom')
    @patch('src.core.resilience.asyncio.sleep')
    async def test_async_retry_uses_secure_random_for_jitter(self, mock_sleep, mock_system_random):
        """Test that async retry logic uses cryptographically secure random for jitter"""
        mock_random_instance = Mock()
        mock_random_instance.random.return_value = 0.7
        mock_system_random.return_value = mock_random_instance
        
        config = RetryConfig(max_attempts=2, base_delay=2.0, jitter=True)
        
        @with_retry(config)
        async def failing_async_function():
            raise ConnectionError("Test connection error")
        
        with pytest.raises(ConnectionError):
            await failing_async_function()
        
        # Verify SystemRandom was used for jitter calculation
        mock_system_random.assert_called()
        mock_random_instance.random.assert_called()
        
        # Verify the delay was calculated with secure jitter
        # delay = base_delay * (exponential_base ** attempt) * (0.5 + secure_random)
        # For first retry: 2.0 * 1 * (0.5 + 0.7) = 2.4
        mock_sleep.assert_called_with(2.4)

    def test_retry_without_jitter_no_random_call(self):
        """Test that retry logic without jitter doesn't use random"""
        config = RetryConfig(max_attempts=2, base_delay=1.0, jitter=False)
        
        @with_retry(config)
        def failing_function():
            raise ValueError("Test error")
        
        with patch('src.core.resilience.secrets.SystemRandom') as mock_system_random:
            with pytest.raises(ValueError):
                failing_function()
            
            # Verify SystemRandom was not called when jitter is disabled
            mock_system_random.assert_not_called()

    def test_secure_random_produces_different_values(self):
        """Test that SystemRandom produces varying jitter values"""
        # This test verifies that we're actually using a proper random source
        secure_random = secrets.SystemRandom()
        
        # Generate multiple random values
        values = [secure_random.random() for _ in range(10)]
        
        # Verify they are all different (extremely unlikely to be the same)
        assert len(set(values)) == len(values)
        
        # Verify they are all in the expected range
        assert all(0 <= v < 1 for v in values)


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in closed state"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)
        
        assert breaker.state == "closed"
        assert not breaker.is_open()
        assert breaker.failure_count == 0

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold"""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test", config)
        
        # First failure
        breaker.record_failure()
        assert breaker.state == "closed"
        assert not breaker.is_open()
        
        # Second failure should open the circuit
        breaker.record_failure()
        assert breaker.state == "open"
        assert breaker.is_open()

    def test_circuit_breaker_success_resets(self):
        """Test successful call resets circuit breaker"""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test", config)
        
        breaker.record_failure()
        assert breaker.failure_count == 1
        
        breaker.record_success()
        assert breaker.failure_count == 0
        assert breaker.state == "closed"


class TestGracefulDegradation:
    """Test graceful degradation functionality"""

    async def test_graceful_degradation_context_manager(self):
        """Test graceful degradation as context manager"""
        async def primary_func():
            return "primary"
        
        async def fallback_func():
            return "fallback"
        
        async with GracefulDegradation(primary=primary_func, fallback=fallback_func) as gd:
            result = await gd.try_primary()
            assert result == "primary"

    async def test_graceful_degradation_fallback_on_failure(self):
        """Test fallback is used when primary fails"""
        async def failing_primary():
            raise ValueError("Primary failed")
        
        async def fallback_func():
            return "fallback_used"
        
        async with GracefulDegradation(primary=failing_primary, fallback=fallback_func) as gd:
            result = await gd.try_primary()
            assert result is None  # Primary failed
            
            fallback_result = await gd.use_fallback()
            assert fallback_result == "fallback_used"


class TestWithFallback:
    """Test fallback decorator"""

    async def test_fallback_decorator_async_success(self):
        """Test fallback decorator with successful async function"""
        async def fallback():
            return "fallback"
        
        @with_fallback(fallback)
        async def primary():
            return "success"
        
        result = await primary()
        assert result == "success"

    async def test_fallback_decorator_async_failure(self):
        """Test fallback decorator with failing async function"""
        async def fallback():
            return "fallback_used"
        
        @with_fallback(fallback)
        async def primary():
            raise RuntimeError("Primary failed")
        
        result = await primary()
        assert result == "fallback_used"

    def test_fallback_decorator_sync_success(self):
        """Test fallback decorator with successful sync function"""
        def fallback():
            return "fallback"
        
        @with_fallback(fallback)
        def primary():
            return "success"
        
        result = primary()
        assert result == "success"

    def test_fallback_decorator_sync_failure(self):
        """Test fallback decorator with failing sync function"""
        def fallback():
            return "fallback_used"
        
        @with_fallback(fallback)
        def primary():
            raise RuntimeError("Primary failed")
        
        result = primary()
        assert result == "fallback_used"


class TestWithCircuitBreaker:
    """Test circuit breaker decorator"""

    def test_circuit_breaker_decorator_success(self):
        """Test circuit breaker decorator with successful function"""
        @with_circuit_breaker("test_success")
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"

    def test_circuit_breaker_decorator_failure_opens_circuit(self):
        """Test circuit breaker decorator opens circuit after failures"""
        config = CircuitBreakerConfig(failure_threshold=1)
        
        @with_circuit_breaker("test_failure", config)
        def failing_func():
            raise RuntimeError("Function failed")
        
        # First call should fail and open the circuit
        with pytest.raises(RuntimeError):
            failing_func()
        
        # Second call should be blocked by open circuit
        with pytest.raises(Exception, match="Circuit breaker 'test_failure' is open"):
            failing_func()