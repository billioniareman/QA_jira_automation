"""Guardrails for tool execution and safety."""

import logging
import time
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from config import settings


logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API calls per user/IP."""

    def __init__(self):
        self._user_calls: Dict[str, list] = defaultdict(list)  # user_id -> [timestamps]
        self._ip_calls: Dict[str, list] = defaultdict(list)  # ip -> [timestamps]

    def check_user_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit."""
        now = time.time()
        minute_ago = now - 60

        # Clean old timestamps
        self._user_calls[user_id] = [
            ts for ts in self._user_calls[user_id] if ts > minute_ago
        ]

        if len(self._user_calls[user_id]) >= settings.RATE_LIMIT_MESSAGES_PER_MINUTE:
            logger.warning(f'User {user_id} exceeded per-minute rate limit')
            return False

        self._user_calls[user_id].append(now)
        return True

    def check_ip_limit(self, ip: str) -> bool:
        """Check if IP has exceeded rate limit."""
        now = time.time()
        minute_ago = now - 60

        # Clean old timestamps
        self._ip_calls[ip] = [ts for ts in self._ip_calls[ip] if ts > minute_ago]

        if len(self._ip_calls[ip]) >= settings.RATE_LIMIT_MESSAGES_PER_MINUTE:
            logger.warning(f'IP {ip} exceeded per-minute rate limit')
            return False

        self._ip_calls[ip].append(now)
        return True


class InputValidator:
    """Validate user inputs for safety and size limits."""

    @staticmethod
    def validate_message(message: str) -> tuple[bool, Optional[str]]:
        """
        Validate user message.
        
        Returns:
            (is_valid, error_message)
        """
        if not message or not message.strip():
            return False, 'Message cannot be empty'

        if len(message) > settings.CHAT_MAX_INPUT_LENGTH:
            return False, f'Message exceeds max length of {settings.CHAT_MAX_INPUT_LENGTH}'

        # Basic injection check
        if InputValidator._has_injection_patterns(message):
            return False, 'Message contains potentially unsafe patterns'

        return True, None

    @staticmethod
    def _has_injection_patterns(text: str) -> bool:
        """Check for common injection patterns."""
        dangerous_patterns = [
            '<?php',
            '<%',
            'DROP TABLE',
            'DELETE FROM',
            'INSERT INTO',
            'UPDATE ',
            '__import__',
            'eval(',
            'exec(',
            'os.system',
        ]

        text_upper = text.upper()
        return any(pattern in text_upper for pattern in dangerous_patterns)


class OutputValidator:
    """Validate LLM and tool outputs."""

    @staticmethod
    def validate_response(response: str) -> tuple[bool, Optional[str]]:
        """
        Validate LLM response.
        
        Returns:
            (is_valid, error_message)
        """
        if not response:
            return False, 'Response is empty'

        if len(response) > settings.CHAT_MAX_OUTPUT_LENGTH:
            return False, f'Response exceeds max length of {settings.CHAT_MAX_OUTPUT_LENGTH}'

        # Check for credential leakage
        if OutputValidator._has_credential_patterns(response):
            return False, 'Response contains potential credentials or sensitive data'

        return True, None

    @staticmethod
    def _has_credential_patterns(text: str) -> bool:
        """Check for credential patterns that should not be exposed."""
        patterns = [
            'api_key',
            'api-key',
            'apikey',
            'password',
            'secret',
            'token',
            'bearer ',
            'authorization: ',
        ]

        text_lower = text.lower()
        return any(pattern in text_lower for pattern in patterns)

    @staticmethod
    def sanitize_jira_urls(response: str) -> str:
        """Remove or mask Jira URLs from response."""
        # Simple replacement - could be more sophisticated
        import re
        response = re.sub(r'https?://[^\s]+\.atlassian\.net[^\s]*', '[Jira URL]', response)
        return response


class ToolExecutionGuardrails:
    """Guardrails for tool execution."""

    def __init__(self):
        self._call_counts: Dict[str, int] = defaultdict(int)  # thread_id -> call count
        self._last_reset: Dict[str, float] = {}  # thread_id -> timestamp

    def check_tool_call_limit(self, thread_id: str) -> bool:
        """Check if thread has exceeded tool call limit."""
        now = time.time()

        # Reset counter if timeout exceeded
        if thread_id in self._last_reset:
            if now - self._last_reset[thread_id] > 300:  # 5 min timeout
                self._call_counts[thread_id] = 0

        if self._call_counts[thread_id] >= settings.CHAT_MAX_TOOL_CALLS:
            logger.warning(
                f'Thread {thread_id} exceeded max tool calls ({settings.CHAT_MAX_TOOL_CALLS})'
            )
            return False

        self._call_counts[thread_id] += 1
        self._last_reset[thread_id] = now
        return True

    def get_remaining_calls(self, thread_id: str) -> int:
        """Get remaining tool calls for a thread."""
        return max(0, settings.CHAT_MAX_TOOL_CALLS - self._call_counts[thread_id])


# Global instances
rate_limiter = RateLimiter()
input_validator = InputValidator()
output_validator = OutputValidator()
tool_execution_guardrails = ToolExecutionGuardrails()
