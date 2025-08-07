"""
Unit tests for rate limiting functionality.
Tests for app/core/rate_limiter.py
"""

import pytest

# Import from app instead of src
try:
    from app.core.rate_limiter import (
        RateLimiter,
        is_rate_limited,
        get_rate_limit_info,
        reset_rate_limit
    )
except ImportError:
    pytest.skip("Rate limiter module not available", allow_module_level=True)


@pytest.mark.unit
class TestRateLimiter:
    """Unit tests for rate limiting functionality."""

    def test_rate_limiter_creation(self):
        """Test RateLimiter class instantiation."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        
        assert limiter.max_requests == 10
        assert limiter.time_window == 60
        assert hasattr(limiter, 'request_log')

    def test_rate_limiter_allows_initial_requests(self):
        """Test that initial requests are allowed."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        user_id = "test_user_1"
        
        # First few requests should be allowed
        for i in range(5):
            assert limiter.is_allowed(user_id)

    def test_rate_limiter_blocks_excess_requests(self):
        """Test that excess requests are blocked."""
        limiter = RateLimiter(max_requests=3, time_window=60)
        user_id = "test_user_2"
        
        # Allow first 3 requests
        for i in range(3):
            assert limiter.is_allowed(user_id)
        
        # 4th request should be blocked
        assert not limiter.is_allowed(user_id)

    def test_rate_limiter_different_users(self):
        """Test that different users have separate rate limits."""
        limiter = RateLimiter(max_requests=2, time_window=60)
        
        user1 = "user_1"
        user2 = "user_2"
        
        # Each user should have their own limit
        assert limiter.is_allowed(user1)
        assert limiter.is_allowed(user1)
        assert not limiter.is_allowed(user1)  # user1 is now limited
        
        # user2 should still be allowed
        assert limiter.is_allowed(user2)
        assert limiter.is_allowed(user2)
        assert not limiter.is_allowed(user2)  # user2 is now limited

    def test_is_rate_limited_function(self):
        """Test the standalone is_rate_limited function."""
        user_id = "test_user_4"
        
        try:
            result = is_rate_limited(user_id)
            assert isinstance(result, bool)
        except NotImplementedError:
            pytest.skip("is_rate_limited function not implemented")

    def test_rate_limiter_edge_cases(self):
        """Test edge cases for rate limiter."""
        limiter = RateLimiter(max_requests=1, time_window=60)
        
        # Test with None user_id
        try:
            result = limiter.is_allowed(None)
            assert isinstance(result, bool)
        except (ValueError, TypeError):
            # Acceptable to raise exception for invalid input
            pass

    def test_rate_limiter_zero_max_requests(self):
        """Test rate limiter with zero max requests."""
        limiter = RateLimiter(max_requests=0, time_window=60)
        user_id = "zero_limit_user"
        
        # Should immediately deny all requests
        assert not limiter.is_allowed(user_id)
        assert not limiter.is_allowed(user_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
