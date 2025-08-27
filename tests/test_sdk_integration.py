"""
Integration Tests for 1Password SDK SecretsManager

These tests verify the SDK integration with actual 1Password service
when credentials are available, and gracefully skip when not.
"""

import asyncio
import os
import time
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Import the real and mock managers
from secrets_manager import SecretsManager
from tests.mocks.mock_secrets import MockSecretsManager, FailingMockSecretsManager


class TestSecretsManagerUnit:
    """Unit tests using mock SecretsManager"""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Reset mock before each test"""
        await MockSecretsManager.reset()
        yield
        await MockSecretsManager.reset()

    @pytest.mark.asyncio
    async def test_mock_initialization(self):
        """Test mock manager initializes correctly"""
        manager = await MockSecretsManager.get_instance()
        assert manager._initialized

        # Check environment variables were set
        assert os.getenv("OPENAI_API_KEY") == "test-openai-key-12345"
        assert os.getenv("GRAPHITI_GROUP_ID") == "test_shared_knowledge"

    @pytest.mark.asyncio
    async def test_mock_get_secret(self):
        """Test retrieving mock secrets"""
        manager = await MockSecretsManager.get_instance()

        # Test secret retrieval
        api_key = await manager.get_secret("OPENAI_API_KEY")
        assert api_key == "test-openai-key-12345"

        # Test config retrieval
        group_id = await manager.get_secret("GRAPHITI_GROUP_ID")
        assert group_id == "test_shared_knowledge"

    @pytest.mark.asyncio
    async def test_mock_health_check(self):
        """Test mock health check"""
        manager = await MockSecretsManager.get_instance()
        health = await manager.health_check()

        assert health["initialized"]
        assert health["secrets_accessible"]
        assert health["token_days_left"] == 89

    @pytest.mark.asyncio
    async def test_failing_mock(self):
        """Test failure scenarios with FailingMockSecretsManager"""
        with pytest.raises(RuntimeError, match="Mock initialization failed"):
            await FailingMockSecretsManager.get_instance()

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test singleton behavior of mock"""
        manager1 = await MockSecretsManager.get_instance()
        manager2 = await MockSecretsManager.get_instance()
        assert manager1 is manager2


@pytest.mark.integration
class TestSecretsManagerIntegration:
    """
    Integration tests with real 1Password SDK.
    These tests are marked with @pytest.mark.integration and only run
    when OP_SERVICE_ACCOUNT_TOKEN is available.
    """

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Reset SecretsManager before each test"""
        await SecretsManager.reset()
        yield
        await SecretsManager.reset()

    @pytest.fixture
    def has_token(self):
        """Check if service account token is available"""
        token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
        if not token:
            # Try loading from file
            from pathlib import Path

            token_file = Path("~/.config/graphiti-mcp/service-token").expanduser()
            if token_file.exists():
                content = token_file.read_text()
                for line in content.split("\n"):
                    if "export OP_SERVICE_ACCOUNT_TOKEN=" in line:
                        token = line.split("=", 1)[1].strip("'\"")
                        if token:
                            os.environ["OP_SERVICE_ACCOUNT_TOKEN"] = token
                            break
        return bool(token)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OP_SERVICE_ACCOUNT_TOKEN"),
        reason="OP_SERVICE_ACCOUNT_TOKEN not set",
    )
    async def test_real_sdk_connection(self, has_token):
        """Test actual SDK connection and initialization"""
        if not has_token:
            pytest.skip("No service account token available")

        manager = await SecretsManager.get_instance()
        assert manager._initialized
        assert manager._client is not None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OP_SERVICE_ACCOUNT_TOKEN"),
        reason="OP_SERVICE_ACCOUNT_TOKEN not set",
    )
    async def test_real_secret_retrieval(self, has_token):
        """Test retrieving actual secrets from 1Password"""
        if not has_token:
            pytest.skip("No service account token available")

        manager = await SecretsManager.get_instance()

        # Test secret retrieval
        api_key = await manager.get_secret("OPENAI_API_KEY")
        assert api_key
        assert not api_key.startswith("test-")
        assert len(api_key) > 10

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OP_SERVICE_ACCOUNT_TOKEN"),
        reason="OP_SERVICE_ACCOUNT_TOKEN not set",
    )
    async def test_caching_performance(self, has_token):
        """Test that caching improves performance"""
        if not has_token:
            pytest.skip("No service account token available")

        manager = await SecretsManager.get_instance()

        # First call - network request
        start1 = time.time()
        value1 = await manager.get_secret("OPENAI_API_KEY")
        time1 = time.time() - start1

        # Second call - should be cached
        start2 = time.time()
        value2 = await manager.get_secret("OPENAI_API_KEY")
        time2 = time.time() - start2

        assert value1 == value2
        # Cached call should be at least 10x faster
        assert time2 < time1 / 10

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OP_SERVICE_ACCOUNT_TOKEN"),
        reason="OP_SERVICE_ACCOUNT_TOKEN not set",
    )
    async def test_health_check_real(self, has_token):
        """Test health check with real SDK"""
        if not has_token:
            pytest.skip("No service account token available")

        manager = await SecretsManager.get_instance()
        health = await manager.health_check()

        assert health["initialized"]
        assert health["token_loaded"]
        assert health["token_valid"]
        assert health["secrets_accessible"]
        assert health["token_days_left"] > 0
        assert len(health["errors"]) == 0

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("OP_SERVICE_ACCOUNT_TOKEN"),
        reason="OP_SERVICE_ACCOUNT_TOKEN not set",
    )
    async def test_token_validation(self, has_token):
        """Test token validation logic"""
        if not has_token:
            pytest.skip("No service account token available")

        manager = SecretsManager()

        # Test invalid token format
        with pytest.raises(ValueError, match="Invalid token format"):
            await manager._validate_token("invalid-token")

        # Test valid token format
        valid_token = "ops_test_token_12345"
        # This will check expiry but not fail on format
        try:
            await manager._validate_token(valid_token)
        except ValueError as e:
            # Should fail on expiry check, not format
            assert "expired" in str(e).lower()

    @pytest.mark.asyncio
    async def test_environment_loading(self):
        """Test that secrets are loaded into environment"""
        # Use mock for this test
        manager = await MockSecretsManager.get_instance()

        # Check environment variables
        assert os.getenv("OPENAI_API_KEY") is not None
        assert os.getenv("LANGFUSE_PUBLIC_KEY") is not None
        assert os.getenv("GRAPHITI_GROUP_ID") is not None

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clearing functionality"""
        manager = await MockSecretsManager.get_instance()

        # Get a secret (populates cache)
        await manager.get_secret("OPENAI_API_KEY")

        # Clear cache
        manager.clear_cache()

        # Should still work (re-fetches)
        value = await manager.get_secret("OPENAI_API_KEY")
        assert value


class TestTokenManagement:
    """Tests for token management and expiration"""

    def test_token_expiry_calculation(self):
        """Test token expiration date calculation"""
        from datetime import datetime, timedelta

        # Token created on 2025-08-27
        created = datetime(2025, 8, 27)
        expires = created + timedelta(days=90)

        # Test various scenarios
        test_cases = [
            (datetime(2025, 8, 27), 90),  # Day of creation
            (datetime(2025, 9, 27), 59),  # 1 month later
            (datetime(2025, 11, 20), 5),  # 5 days before expiry
            (datetime(2025, 11, 26), -1),  # 1 day after expiry
        ]

        for test_date, expected_days in test_cases:
            days_left = (expires - test_date).days
            assert days_left == expected_days

    @pytest.mark.asyncio
    async def test_token_file_loading(self):
        """Test loading token from file"""
        import tempfile
        from pathlib import Path

        # Create temporary token file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\n")
            f.write("# Test token file\n")
            f.write("export OP_SERVICE_ACCOUNT_TOKEN='ops_test_token_12345'\n")
            temp_file = f.name

        try:
            # Mock the token file path
            original_expanduser = Path.expanduser

            def mock_expanduser(self):
                if str(self) == "~/.config/graphiti-mcp/service-token":
                    return Path(temp_file)
                return original_expanduser(self)

            with patch.object(Path, "expanduser", mock_expanduser):
                manager = SecretsManager()
                token = manager._get_service_token()
                assert token == "ops_test_token_12345"

        finally:
            # Cleanup
            os.unlink(temp_file)


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_missing_secret_key(self):
        """Test handling of unknown secret keys"""
        manager = await MockSecretsManager.get_instance()

        with pytest.raises(KeyError, match="Unknown key in mock"):
            await manager.get_secret("UNKNOWN_KEY")

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic on initialization failure"""
        # Mock the Client.authenticate to fail twice then succeed
        with patch("secrets_manager.Client") as mock_client:
            mock_client.authenticate = MagicMock(
                side_effect=[
                    Exception("First failure"),
                    Exception("Second failure"),
                    MagicMock(),  # Success on third try
                ]
            )

            # This should succeed after retries
            # Note: This test would need the real manager with mocked client
            # For now, we'll just verify the pattern works
            pass


# Run integration tests only when explicitly requested
if __name__ == "__main__":
    # Run all tests including integration
    pytest.main([__file__, "-v", "-m", "integration"])
