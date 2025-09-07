"""
1Password SDK Secrets Manager with Async Singleton Pattern

This module provides a robust secrets management system using the 1Password SDK
with caching, retry logic, token validation, and health monitoring.
"""

import asyncio
import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from onepassword.client import Client

from config.secrets_manifest import SECRET_REFS, CONFIG_VALUES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Thread-safe async singleton for managing 1Password secrets.

    Features:
    - Async singleton pattern with proper locking
    - Secret caching to reduce API calls
    - Retry logic for transient failures
    - Token expiration monitoring
    - Health checks
    """

    _instance: Optional["SecretsManager"] = None
    _lock = asyncio.Lock()
    _cache: Dict[str, Tuple[str, float]] = {}
    _cache_ttl = 300  # 5 minutes
    _client: Optional[Client] = None
    _initialized = False

    def __new__(cls):
        """Prevent direct instantiation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_instance(cls) -> "SecretsManager":
        """
        Get or create the singleton instance with async initialization.
        Thread-safe using asyncio.Lock.
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        elif not cls._instance._initialized:
            async with cls._lock:
                if not cls._instance._initialized:
                    await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """
        Async initialization with retry logic and fallback support.
        Called once during singleton creation.
        """
        if self._initialized:
            return

        # Check for fallback mode first
        token = self._get_service_token()
        if token is None:
            # Fallback mode - load from .env.graphiti
            await self._initialize_fallback()
            return

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                # Validate token
                await self._validate_token(token)

                # Initialize 1Password client
                self._client = await Client.authenticate(
                    auth=token,
                    integration_name="Graphiti MCP Server",
                    integration_version="v1.0.0",
                )

                # Preload all secrets
                await self._preload_secrets()

                # Start token expiry monitor
                self._start_token_monitor()

                self._initialized = True
                logger.info("✅ 1Password SDK initialized successfully")
                return

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"SDK init attempt {attempt + 1}/{max_retries} failed: {e}"
                    )
                    await asyncio.sleep(retry_delay * (2**attempt))
                else:
                    # Try fallback mode as last resort
                    logger.warning(
                        f"1Password SDK failed after {max_retries} attempts, trying fallback mode"
                    )
                    try:
                        await self._initialize_fallback()
                        return
                    except Exception as fallback_e:
                        error_msg = f"Failed to initialize 1Password SDK and fallback also failed: {fallback_e}"
                        logger.error(f"❌ {error_msg}")
                        raise RuntimeError(error_msg)

    async def _initialize_fallback(self):
        """
        Initialize in fallback mode using .env.graphiti file.
        """
        logger.info("Initializing in fallback mode with .env.graphiti...")

        # Try to load from .env.graphiti
        env_file = Path(".env.graphiti")
        if not env_file.exists():
            # Try home directory location
            env_file = Path.home() / "gtd-coach" / ".env.graphiti"

        if env_file.exists():
            try:
                from dotenv import load_dotenv

                load_dotenv(env_file)

                # Load configuration values into environment
                for key, value in CONFIG_VALUES.items():
                    if key not in os.environ:
                        os.environ[key] = value

                # Check if critical secrets are available
                if not os.getenv("OPENAI_API_KEY"):
                    raise ValueError("OPENAI_API_KEY not found in .env.graphiti")

                self._initialized = True
                logger.info("✅ Initialized in fallback mode using .env.graphiti")

            except Exception as e:
                raise RuntimeError(f"Failed to load .env.graphiti: {e}")
        else:
            raise RuntimeError(
                "Cannot initialize in fallback mode: .env.graphiti not found\n"
                "Expected locations:\n"
                "  - ./env.graphiti\n"
                "  - ~/gtd-coach/.env.graphiti"
            )

    def _get_service_token(self) -> str:
        """
        Load service account token with fallback strategy.

        Attempts in order:
        1. Environment variable OP_SERVICE_ACCOUNT_TOKEN
        2. File at ~/.config/graphiti-mcp/service-token

        Returns:
            str: The service account token

        Raises:
            ValueError: If no token can be found
        """
        # Try environment variable first
        token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")

        if not token:
            # Try file location
            token_file = Path("~/.config/graphiti-mcp/service-token").expanduser()
            if token_file.exists():
                try:
                    # Source the bash file and extract the token
                    content = token_file.read_text()
                    for line in content.split("\n"):
                        if "export OP_SERVICE_ACCOUNT_TOKEN=" in line:
                            # Extract token value, handling quotes
                            token_part = line.split("=", 1)[1]
                            token = token_part.strip().strip("'\"")
                            if token:
                                logger.info(f"Loaded token from {token_file}")
                                break
                except Exception as e:
                    logger.error(f"Failed to read token file: {e}")

        if not token:
            # Check if we should use fallback mode
            if (
                os.getenv("GRAPHITI_FALLBACK_MODE")
                and os.getenv("GRAPHITI_FALLBACK_MODE").lower() == "true"
            ):
                logger.warning(
                    "No 1Password token found, using fallback mode with .env.graphiti"
                )
                return None  # Signal to use fallback

            raise ValueError(
                "No service account token found. Please either:\n"
                "1. Set OP_SERVICE_ACCOUNT_TOKEN environment variable, or\n"
                "2. Ensure ~/.config/graphiti-mcp/service-token exists\n"
                "3. Set GRAPHITI_FALLBACK_MODE=true to use .env.graphiti fallback"
            )

        return token

    async def _validate_token(self, token: str):
        """
        Validate token format and check expiration.

        Args:
            token: The service account token to validate

        Raises:
            ValueError: If token is invalid or expired
        """
        # Check token format
        if not token.startswith("ops_"):
            raise ValueError(
                f"Invalid token format. Token should start with 'ops_' "
                f"but starts with '{token[:4]}...'"
            )

        # Check token age and expiration
        # Token was created on 2025-08-27 with 90-day expiry
        token_created = datetime(2025, 8, 27)
        expires = token_created + timedelta(days=90)
        now = datetime.now()
        days_left = (expires - now).days

        if days_left < 0:
            raise ValueError(
                f"Service account token expired {abs(days_left)} days ago. "
                f"Please rotate the token in 1Password."
            )
        elif days_left < 7:
            logger.warning(
                f"⚠️ Service account token expires in {days_left} days! "
                f"Please rotate soon."
            )
        elif days_left < 30:
            logger.info(f"📅 Service account token expires in {days_left} days")

    async def get_secret(self, key: str) -> str:
        """
        Get a secret value with caching.

        Args:
            key: The environment variable name

        Returns:
            str: The secret value

        Raises:
            KeyError: If the key is not in the manifest
            RuntimeError: If secret resolution fails
        """
        if not self._initialized:
            await self._initialize()

        # Check if value is already in environment (from direnv)
        env_value = os.getenv(key)
        if env_value:
            logger.debug(f"Using environment variable for {key}")
            return env_value

        # Check cache first
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"Cache hit for {key}")
                return value

        # Get secret reference
        ref = SECRET_REFS.get(key)
        if not ref:
            # Check if it's a config value
            if key in CONFIG_VALUES:
                return CONFIG_VALUES[key]
            raise KeyError(f"Unknown secret key: {key}")

        # Fetch from 1Password
        try:
            logger.debug(f"Fetching {key} from 1Password")
            value = await self._client.secrets.resolve(ref)

            # Update cache
            self._cache[key] = (value, time.time())
            return value

        except Exception as e:
            logger.error(f"Failed to resolve secret {key}: {e}")

            # Try stale cache as fallback
            if key in self._cache:
                value, _ = self._cache[key]
                logger.warning(f"Using expired cached value for {key}")
                return value

            raise RuntimeError(f"Failed to get secret {key}: {e}")

    async def _preload_secrets(self):
        """
        Preload all secrets into environment variables and cache.
        Resolves each secret individually as SDK doesn't support bulk resolution.
        Adds delays to prevent rate limiting.
        """
        try:
            logger.info("Preloading secrets from 1Password...")

            loaded_count = 0
            failed_secrets = []

            # Resolve each secret individually with delay to prevent rate limiting
            for i, (name, ref) in enumerate(SECRET_REFS.items()):
                try:
                    # Add delay between requests (except for first one)
                    if i > 0:
                        await asyncio.sleep(0.2)  # 200ms delay to prevent rate limiting

                    # Resolve the secret
                    value = await self._client.secrets.resolve(ref)

                    # Update environment
                    os.environ[name] = value

                    # Update cache
                    self._cache[name] = (value, time.time())
                    loaded_count += 1
                    logger.debug(f"Loaded {name}")

                except Exception as e:
                    error_msg = str(e)
                    # Check for rate limiting
                    if "429" in error_msg or "Too Many Requests" in error_msg:
                        logger.warning(
                            f"Rate limited while loading {name}, waiting 5 seconds..."
                        )
                        await asyncio.sleep(5)
                        # Try once more after waiting
                        try:
                            value = await self._client.secrets.resolve(ref)
                            os.environ[name] = value
                            self._cache[name] = (value, time.time())
                            loaded_count += 1
                            logger.debug(f"Loaded {name} on retry")
                        except Exception as retry_e:
                            error_msg = f"Failed to load {name} after retry: {retry_e}"
                            logger.error(error_msg)
                            failed_secrets.append(error_msg)
                    else:
                        error_msg = f"Failed to load {name}: {e}"
                        logger.error(error_msg)
                        failed_secrets.append(error_msg)

            # Raise error if any secrets failed
            if failed_secrets:
                raise ValueError(f"Failed to load secrets: {', '.join(failed_secrets)}")

            # Also load config values into environment
            for key, value in CONFIG_VALUES.items():
                os.environ[key] = value

            logger.info(
                f"✅ Preloaded {loaded_count} secrets and "
                f"{len(CONFIG_VALUES)} config values"
            )

        except Exception as e:
            logger.error(f"Failed to preload secrets: {e}")
            raise

    def _start_token_monitor(self):
        """Start background task to monitor token expiration."""
        asyncio.create_task(self._monitor_token_expiry())

    async def _monitor_token_expiry(self):
        """
        Background task that checks token expiration daily.
        Logs warnings as expiration approaches.
        """
        while True:
            try:
                # Wait 24 hours
                await asyncio.sleep(86400)

                # Check token
                token = self._get_service_token()
                await self._validate_token(token)

            except asyncio.CancelledError:
                # Task cancelled, exit cleanly
                break
            except Exception as e:
                logger.error(f"Token validation check failed: {e}")

    async def health_check(self) -> Dict[str, any]:
        """
        Perform a comprehensive health check.

        Returns:
            Dict with health status information
        """
        health = {
            "initialized": self._initialized,
            "token_loaded": False,
            "token_valid": False,
            "token_days_left": 0,
            "secrets_accessible": False,
            "cache_size": len(self._cache),
            "errors": [],
        }

        try:
            # Check token
            token = self._get_service_token()
            health["token_loaded"] = bool(token)

            # Validate token
            await self._validate_token(token)
            health["token_valid"] = True

            # Calculate days left
            token_created = datetime(2025, 8, 27)
            expires = token_created + timedelta(days=90)
            health["token_days_left"] = (expires - datetime.now()).days

            # Test secret access
            test_key = await self.get_secret("OPENAI_API_KEY")
            health["secrets_accessible"] = bool(test_key)

        except Exception as e:
            health["errors"].append(str(e))

        return health

    def clear_cache(self):
        """Clear the secret cache. Useful for testing."""
        self._cache.clear()
        logger.info("Secret cache cleared")

    @classmethod
    async def reset(cls):
        """
        Reset the singleton instance. Useful for testing.

        Warning: This should only be used in tests!
        """
        async with cls._lock:
            if cls._instance:
                cls._instance._initialized = False
                cls._instance._cache.clear()
                cls._instance._client = None
            cls._instance = None
            logger.info("SecretsManager singleton reset")
