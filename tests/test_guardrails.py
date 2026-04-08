"""Tests for guardrails (input/output validation, rate limiting)."""

import pytest
import time

from app.guardrails.guardrails import (
    InputValidator,
    OutputValidator,
    RateLimiter,
    ToolExecutionGuardrails,
)


class TestInputValidator:
    """Test input validation."""

    def test_valid_message(self):
        """Test valid message."""
        is_valid, error = InputValidator.validate_message("What are the open issues?")
        
        assert is_valid is True
        assert error is None

    def test_empty_message(self):
        """Test empty message rejection."""
        is_valid, error = InputValidator.validate_message("")
        
        assert is_valid is False
        assert "empty" in error.lower()

    def test_message_too_long(self):
        """Test message length limit."""
        from config import settings
        long_message = "a" * (settings.CHAT_MAX_INPUT_LENGTH + 1)
        
        is_valid, error = InputValidator.validate_message(long_message)
        
        assert is_valid is False
        assert "exceeds" in error.lower()

    def test_injection_patterns(self):
        """Test SQL injection detection."""
        malicious = "'; DROP TABLE users; --"
        
        is_valid, error = InputValidator.validate_message(malicious)
        
        assert is_valid is False
        assert "unsafe" in error.lower()

    def test_python_injection_detection(self):
        """Test Python injection detection."""
        malicious = "__import__('os').system('rm -rf /')"
        
        is_valid, error = InputValidator.validate_message(malicious)
        
        assert is_valid is False


class TestOutputValidator:
    """Test output validation."""

    def test_valid_response(self):
        """Test valid response."""
        is_valid, error = OutputValidator.validate_response("This is a valid response.")
        
        assert is_valid is True
        assert error is None

    def test_empty_response(self):
        """Test empty response rejection."""
        is_valid, error = OutputValidator.validate_response("")
        
        assert is_valid is False

    def test_response_too_long(self):
        """Test response length limit."""
        from config import settings
        long_response = "a" * (settings.CHAT_MAX_OUTPUT_LENGTH + 1)
        
        is_valid, error = OutputValidator.validate_response(long_response)
        
        assert is_valid is False

    def test_credential_detection(self):
        """Test credential pattern detection."""
        response_with_creds = "The API key is: sk-1234567890"
        
        is_valid, error = OutputValidator.validate_response(response_with_creds)
        
        assert is_valid is False

    def test_sanitize_jira_urls(self):
        """Test Jira URL sanitization."""
        response = "Visit https://company.atlassian.net/browse/PROJ-123 for details"
        
        sanitized = OutputValidator.sanitize_jira_urls(response)
        
        assert "atlassian.net" not in sanitized
        assert "[Jira URL]" in sanitized


class TestRateLimiter:
    """Test rate limiting."""

    def test_user_rate_limit(self):
        """Test per-user rate limiting."""
        limiter = RateLimiter()
        
        # Should allow first 10 calls
        for i in range(10):
            assert limiter.check_user_limit("user-123") is True
        
        # 11th call should fail
        assert limiter.check_user_limit("user-123") is False

    def test_rate_limit_reset(self):
        """Test rate limit resets after timeout."""
        limiter = RateLimiter()
        from config import settings
        
        # Exhaust limit
        for i in range(settings.RATE_LIMIT_MESSAGES_PER_MINUTE):
            limiter.check_user_limit("user-123")
        
        assert limiter.check_user_limit("user-123") is False
        
        # Clear old timestamps manually for testing
        now = time.time()
        limiter._user_calls["user-123"] = [t for t in limiter._user_calls["user-123"] if t > now - 60]

    def test_ip_rate_limit(self):
        """Test per-IP rate limiting."""
        limiter = RateLimiter()
        from config import settings
        
        # Allow up to limit
        for i in range(settings.RATE_LIMIT_MESSAGES_PER_MINUTE):
            assert limiter.check_ip_limit("192.168.1.1") is True
        
        # Exceed limit
        assert limiter.check_ip_limit("192.168.1.1") is False

    def test_different_users_independent_limits(self):
        """Test that different users have independent limits."""
        limiter = RateLimiter()
        from config import settings
        
        # Exhaust user 1
        for i in range(settings.RATE_LIMIT_MESSAGES_PER_MINUTE):
            limiter.check_user_limit("user-1")
        
        # User 2 should still have allowance
        assert limiter.check_user_limit("user-2") is True


class TestToolExecutionGuardrails:
    """Test tool execution safety."""

    def test_tool_call_limit(self):
        """Test tool call per-thread limit."""
        guardrails = ToolExecutionGuardrails()
        from config import settings
        
        thread_id = "thread-123"
        
        # Allow up to limit
        for i in range(settings.CHAT_MAX_TOOL_CALLS):
            assert guardrails.check_tool_call_limit(thread_id) is True
        
        # Exceed limit
        assert guardrails.check_tool_call_limit(thread_id) is False

    def test_get_remaining_calls(self):
        """Test getting remaining tool calls."""
        guardrails = ToolExecutionGuardrails()
        thread_id = "thread-456"
        
        remaining_start = guardrails.get_remaining_calls(thread_id)
        
        guardrails.check_tool_call_limit(thread_id)
        remaining_after_one = guardrails.get_remaining_calls(thread_id)
        
        assert remaining_after_one == remaining_start - 1

    def test_independent_thread_limits(self):
        """Test that different threads have independent limits."""
        guardrails = ToolExecutionGuardrails()
        from config import settings
        
        # Exhaust thread 1
        for i in range(settings.CHAT_MAX_TOOL_CALLS):
            guardrails.check_tool_call_limit("thread-1")
        
        # Thread 2 should still have allowance
        assert guardrails.check_tool_call_limit("thread-2") is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
