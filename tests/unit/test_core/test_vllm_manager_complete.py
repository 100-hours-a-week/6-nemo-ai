"""
Unit tests for VLLM Manager functionality.
Tests for app/core/vllm_manager.py
"""

import pytest
import asyncio
import time
import httpx
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Import from app instead of src
try:
    from app.core.vllm_manager import (
        CircuitBreaker,
        CircuitBreakerState,
        CircuitBreakerConfig,
        RetryConfig,
        VLLMHealthMonitor,
        VLLMManager
    )
except ImportError:
    pytest.skip("VLLM Manager module not available", allow_module_level=True)


@pytest.mark.unit
class TestCircuitBreakerConfig:
    """Unit tests for CircuitBreakerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 2

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=1
        )
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.success_threshold == 1


@pytest.mark.unit
class TestRetryConfig:
    """Unit tests for RetryConfig dataclass."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 10.0
        assert config.exponential_base == 2.0

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=20.0,
            exponential_base=1.5
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 20.0
        assert config.exponential_base == 1.5


@pytest.mark.unit
class TestCircuitBreaker:
    """Unit tests for CircuitBreaker class."""

    def test_circuit_breaker_initialization(self):
        """Test CircuitBreaker initialization."""
        cb = CircuitBreaker()
        
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None
        assert cb.lock is not None

    def test_circuit_breaker_custom_config(self):
        """Test CircuitBreaker with custom config."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)
        
        assert cb.config.failure_threshold == 3

    @pytest.mark.asyncio
    async def test_is_request_allowed_closed_state(self):
        """Test request allowed in CLOSED state."""
        cb = CircuitBreaker()
        
        allowed = await cb.is_request_allowed()
        assert allowed is True

    @pytest.mark.asyncio
    async def test_is_request_allowed_open_state(self):
        """Test request blocked in OPEN state."""
        cb = CircuitBreaker()
        cb.state = CircuitBreakerState.OPEN
        cb.last_failure_time = time.time()
        
        allowed = await cb.is_request_allowed()
        assert allowed is False

    @pytest.mark.asyncio
    async def test_state_transition_open_to_half_open(self):
        """Test state transition from OPEN to HALF_OPEN."""
        config = CircuitBreakerConfig(recovery_timeout=0.1)
        cb = CircuitBreaker(config)
        
        # Set to OPEN state with old failure time
        cb.state = CircuitBreakerState.OPEN
        cb.last_failure_time = time.time() - 1.0  # 1 second ago
        
        allowed = await cb.is_request_allowed()
        assert allowed is True
        assert cb.state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_record_success_closed_state(self):
        """Test recording success in CLOSED state."""
        cb = CircuitBreaker()
        cb.failure_count = 2
        
        await cb.record_success()
        
        assert cb.failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_record_success_half_open_to_closed(self):
        """Test state transition from HALF_OPEN to CLOSED on success."""
        config = CircuitBreakerConfig(success_threshold=2)
        cb = CircuitBreaker(config)
        cb.state = CircuitBreakerState.HALF_OPEN
        
        # First success
        await cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb.success_count == 1
        
        # Second success should close circuit
        await cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_record_failure_closed_to_open(self):
        """Test state transition from CLOSED to OPEN on failures."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config)
        
        # First failure
        await cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 1
        
        # Second failure should open circuit
        await cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_record_failure_half_open_to_open(self):
        """Test state transition from HALF_OPEN to OPEN on failure."""
        cb = CircuitBreaker()
        cb.state = CircuitBreakerState.HALF_OPEN
        
        await cb.record_failure()
        
        assert cb.state == CircuitBreakerState.OPEN


@pytest.mark.unit
class TestVLLMHealthMonitor:
    """Unit tests for VLLMHealthMonitor class."""

    def test_health_monitor_initialization(self):
        """Test VLLMHealthMonitor initialization."""
        monitor = VLLMHealthMonitor()
        
        assert monitor.success_count == 0
        assert monitor.failure_count == 0
        assert monitor.response_times == []
        assert monitor.last_health_check is None
        assert monitor.is_healthy is True

    def test_record_success(self):
        """Test recording successful responses."""
        monitor = VLLMHealthMonitor()
        
        monitor.record_success(1.5)
        
        assert monitor.success_count == 1
        assert monitor.response_times == [1.5]

    def test_record_success_response_time_limit(self):
        """Test response time history limit."""
        monitor = VLLMHealthMonitor()
        monitor.max_response_time_history = 3
        
        # Add more response times than limit
        for i in range(5):
            monitor.record_success(float(i))
        
        assert len(monitor.response_times) == 3
        assert monitor.response_times == [2.0, 3.0, 4.0]  # Last 3

    def test_record_failure(self):
        """Test recording failures."""
        monitor = VLLMHealthMonitor()
        
        monitor.record_failure()
        
        assert monitor.failure_count == 1

    def test_get_metrics_empty(self):
        """Test metrics with no data."""
        monitor = VLLMHealthMonitor()
        
        metrics = monitor.get_metrics()
        
        assert metrics['success_rate'] == 0
        assert metrics['total_requests'] == 0
        assert metrics['avg_response_time'] == 0
        assert metrics['p95_response_time'] == 0

    def test_get_metrics_with_data(self):
        """Test metrics calculation with data."""
        monitor = VLLMHealthMonitor()
        
        # Add some successes and failures
        monitor.record_success(1.0)
        monitor.record_success(2.0)
        monitor.record_success(3.0)
        monitor.record_failure()
        
        metrics = monitor.get_metrics()
        
        assert metrics['success_rate'] == 0.75  # 3/4
        assert metrics['total_requests'] == 4
        assert metrics['success_count'] == 3
        assert metrics['failure_count'] == 1
        assert metrics['avg_response_time'] == 2.0  # (1+2+3)/3
        assert metrics['is_healthy'] is True

    def test_get_metrics_p95_calculation(self):
        """Test P95 response time calculation."""
        monitor = VLLMHealthMonitor()
        
        # Add 20 response times (1.0 to 20.0)
        for i in range(1, 21):
            monitor.record_success(float(i))
        
        metrics = monitor.get_metrics()
        
        # P95 of 1-20 should be around 19
        assert metrics['p95_response_time'] >= 19.0

    @pytest.mark.asyncio
    async def test_health_check_empty_url(self):
        """Test health check with empty URL."""
        monitor = VLLMHealthMonitor()
        
        result = await monitor.health_check("")
        
        assert result is False
        assert monitor.is_healthy is False
        assert monitor.last_health_check is not None

    @pytest.mark.asyncio
    async def test_health_check_invalid_url(self):
        """Test health check with invalid URL."""
        monitor = VLLMHealthMonitor()
        
        result = await monitor.health_check("invalid-url")
        
        assert result is False
        assert monitor.is_healthy is False

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_health_check_success(self, mock_client):
        """Test successful health check."""
        monitor = VLLMHealthMonitor()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_context_manager
        mock_context_manager.get.return_value = mock_response
        
        mock_client.return_value = mock_context_manager
        
        result = await monitor.health_check("http://localhost:8000")
        
        assert result is True
        assert monitor.is_healthy is True

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_health_check_timeout(self, mock_client):
        """Test health check timeout."""
        monitor = VLLMHealthMonitor()
        
        # Mock timeout exception
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_context_manager
        mock_context_manager.get.side_effect = httpx.TimeoutException("Timeout")
        
        mock_client.return_value = mock_context_manager
        
        result = await monitor.health_check("http://localhost:8000")
        
        assert result is False
        assert monitor.is_healthy is False


@pytest.mark.unit
class TestVLLMManager:
    """Unit tests for VLLMManager class."""

    def test_vllm_manager_initialization(self):
        """Test VLLMManager initialization."""
        manager = VLLMManager("http://localhost:8000")
        
        assert manager.vllm_url == "http://localhost:8000"
        assert isinstance(manager.retry_config, RetryConfig)
        assert isinstance(manager.circuit_breaker, CircuitBreaker)
        assert isinstance(manager.health_monitor, VLLMHealthMonitor)

    def test_vllm_manager_url_stripping(self):
        """Test URL trailing slash removal."""
        manager = VLLMManager("http://localhost:8000/")
        
        assert manager.vllm_url == "http://localhost:8000"

    def test_vllm_manager_custom_configs(self):
        """Test VLLMManager with custom configurations."""
        retry_config = RetryConfig(max_retries=5)
        circuit_config = CircuitBreakerConfig(failure_threshold=3)
        
        manager = VLLMManager(
            "http://localhost:8000",
            retry_config=retry_config,
            circuit_config=circuit_config
        )
        
        assert manager.retry_config.max_retries == 5
        assert manager.circuit_breaker.config.failure_threshold == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_circuit_breaker_open(self):
        """Test execute_with_retry when circuit breaker is open."""
        manager = VLLMManager("http://localhost:8000")
        
        # Set circuit breaker to open
        manager.circuit_breaker.state = CircuitBreakerState.OPEN
        manager.circuit_breaker.last_failure_time = time.time()
        
        async def dummy_operation():
            return "success"
        
        with pytest.raises(RuntimeError, match="vLLM 서비스가 일시적으로 사용할 수 없습니다"):
            await manager.execute_with_retry(dummy_operation)

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self):
        """Test successful operation with retry mechanism."""
        manager = VLLMManager("http://localhost:8000")
        
        async def dummy_operation():
            return "success"
        
        result = await manager.execute_with_retry(dummy_operation)
        
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_retry_failure_then_success(self):
        """Test retry mechanism with initial failure then success."""
        manager = VLLMManager("http://localhost:8000")
        
        call_count = 0
        
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("First call timeout")
            return "success on retry"
        
        result = await manager.execute_with_retry(flaky_operation)
        
        assert result == "success on retry"
        assert call_count == 2

    def test_get_health_metrics(self):
        """Test health metrics retrieval."""
        manager = VLLMManager("http://localhost:8000")
        
        # Add some test data
        manager.circuit_breaker.failure_count = 2
        manager.circuit_breaker.success_count = 8
        manager.health_monitor.record_success(1.5)
        manager.health_monitor.record_failure()
        
        metrics = manager.get_health_metrics()
        
        assert 'circuit_breaker' in metrics
        assert 'health' in metrics
        assert 'timestamp' in metrics
        
        assert metrics['circuit_breaker']['failure_count'] == 2
        assert metrics['circuit_breaker']['success_count'] == 8
        assert metrics['health']['success_count'] == 1
        assert metrics['health']['failure_count'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
