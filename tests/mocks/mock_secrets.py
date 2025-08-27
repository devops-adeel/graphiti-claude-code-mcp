"""
Mock SecretsManager for Unit Testing

This module provides a mock implementation of SecretsManager for testing
without requiring actual 1Password credentials or network access.
"""

import asyncio
from typing import Dict, Optional, Tuple


class MockSecretsManager:
    """
    Mock implementation of SecretsManager for unit tests.

    Provides the same interface as the real SecretsManager but returns
    test values without requiring 1Password SDK or network access.
    """

    # Test secrets for unit tests
    _test_secrets = {
        "OPENAI_API_KEY": "test-openai-key-12345",
        "LANGFUSE_PUBLIC_KEY": "pk-lf-test-00000000-0000-0000-0000-000000000000",
        "LANGFUSE_SECRET_KEY": "sk-lf-test-00000000-0000-0000-0000-000000000000",
        "LANGFUSE_HOST": "https://langfuse.local",
    }

    # Test config values
    _test_config = {
        "GRAPHITI_GROUP_ID": "test_shared_knowledge",
        "FALKORDB_DATABASE": "test_db",
        "FALKORDB_HOST": "localhost",
        "FALKORDB_PORT": "6379",
        "OPENAI_MODEL": "gpt-4o-mini",
        "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
        "MEMORY_DECAY_FACTOR": "0.95",
        "MEMORY_INCLUDE_HISTORICAL": "false",
        "ENABLE_GTD_INTEGRATION": "true",
        "ENABLE_CROSS_REFERENCES": "true",
    }

    _instance: Optional["MockSecretsManager"] = None
    _lock = asyncio.Lock()
    _initialized = False

    def __new__(cls):
        """Prevent direct instantiation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_instance(cls) -> "MockSecretsManager":
        """
        Get mock singleton instance.
        Mimics the real SecretsManager interface.
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """Mock initialization - instant success"""
        if self._initialized:
            return

        # Simulate loading secrets into environment
        import os

        for key, value in self._test_secrets.items():
            os.environ[key] = value
        for key, value in self._test_config.items():
            os.environ[key] = value

        self._initialized = True

    async def get_secret(self, key: str) -> str:
        """
        Get a mock secret value.

        Args:
            key: The environment variable name

        Returns:
            str: The mock secret value
        """
        if key in self._test_secrets:
            return self._test_secrets[key]
        elif key in self._test_config:
            return self._test_config[key]
        else:
            raise KeyError(f"Unknown key in mock: {key}")

    async def health_check(self) -> Dict[str, any]:
        """
        Mock health check - always healthy.

        Returns:
            Dict with mock health status
        """
        return {
            "initialized": True,
            "token_loaded": True,
            "token_valid": True,
            "token_days_left": 89,  # Mock: almost full validity
            "secrets_accessible": True,
            "cache_size": len(self._test_secrets),
            "errors": [],
        }

    def clear_cache(self):
        """Mock cache clear - no-op"""
        pass

    @classmethod
    async def reset(cls):
        """
        Reset mock singleton for test isolation.
        """
        async with cls._lock:
            if cls._instance:
                cls._instance._initialized = False
                # Clear environment variables
                import os

                for key in cls._test_secrets:
                    os.environ.pop(key, None)
                for key in cls._test_config:
                    os.environ.pop(key, None)
            cls._instance = None


class FailingMockSecretsManager(MockSecretsManager):
    """
    Mock that simulates failures for error testing.
    """

    async def _initialize(self):
        """Simulate initialization failure"""
        raise RuntimeError("Mock initialization failed")

    async def get_secret(self, key: str) -> str:
        """Simulate secret retrieval failure"""
        raise RuntimeError(f"Mock failed to get secret: {key}")

    async def health_check(self) -> Dict[str, any]:
        """Simulate unhealthy state"""
        return {
            "initialized": False,
            "token_loaded": False,
            "token_valid": False,
            "token_days_left": -1,  # Expired
            "secrets_accessible": False,
            "cache_size": 0,
            "errors": [
                "Mock error: Token expired",
                "Mock error: Cannot connect to 1Password",
            ],
        }
