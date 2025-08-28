#!/usr/bin/env python3
"""
SSL Configuration Utility for OrbStack and Docker Environments

This module automatically detects and configures SSL certificates for various
container environments, with special support for OrbStack's self-signed certificates.
"""

import os
import ssl
import logging
from pathlib import Path
from typing import Optional, List, Union
import certifi
import httpx

logger = logging.getLogger(__name__)


class SSLConfig:
    """
    Manages SSL certificate configuration for different environments.

    Automatically detects:
    - OrbStack environments with custom CA certificates
    - Standard Docker environments
    - Cloud deployments with proper certificates
    """

    # Common certificate locations
    ORBSTACK_CERT_PATHS = [
        "/usr/local/share/ca-certificates/orbstack-root.crt",
        "/etc/ssl/certs/orbstack-root.crt",
        "~/.orbstack/ssl/ca.crt",
    ]

    SYSTEM_CERT_PATHS = [
        "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu
        "/etc/pki/tls/certs/ca-bundle.crt",  # RHEL/CentOS
        "/etc/ssl/ca-bundle.pem",  # OpenSUSE
        "/etc/ssl/cert.pem",  # Alpine
    ]

    def __init__(self):
        """Initialize SSL configuration with environment detection."""
        self._ssl_context: Optional[ssl.SSLContext] = None
        self._cert_path: Optional[str] = None
        self._environment: Optional[str] = None
        self._detect_environment()

    def _detect_environment(self) -> None:
        """Detect the current environment and available certificates."""
        # Check for OrbStack
        if self._is_orbstack():
            self._environment = "orbstack"
            self._cert_path = self._find_orbstack_cert()
            logger.info(f"OrbStack environment detected, using cert: {self._cert_path}")

        # Check for custom cert from environment
        elif os.environ.get("SSL_CERT_FILE"):
            self._environment = "custom"
            self._cert_path = os.environ["SSL_CERT_FILE"]
            logger.info(f"Custom SSL cert configured: {self._cert_path}")

        # Check for system certificates
        elif system_cert := self._find_system_cert():
            self._environment = "system"
            self._cert_path = system_cert
            logger.info(f"System certificates found: {self._cert_path}")

        # Default to certifi
        else:
            self._environment = "certifi"
            self._cert_path = certifi.where()
            logger.info("Using default certifi certificates")

    def _is_orbstack(self) -> bool:
        """Check if running in OrbStack environment."""
        # Multiple indicators of OrbStack
        indicators = [
            # Check for OrbStack certificate
            any(
                Path(p).expanduser().exists()
                for p in self.ORBSTACK_CERT_PATHS
                if not p.startswith("~") or Path.home().exists()
            ),
            # Check for OrbStack domains in /etc/hosts
            Path("/etc/hosts").exists()
            and ".orb.local" in Path("/etc/hosts").read_text(errors="ignore"),
            # Check environment variable
            "ORBSTACK" in os.environ,
        ]
        return any(indicators)

    def _find_orbstack_cert(self) -> Optional[str]:
        """Find OrbStack CA certificate."""
        for cert_path in self.ORBSTACK_CERT_PATHS:
            path = Path(cert_path).expanduser()
            if path.exists():
                return str(path)

        # If we detected OrbStack but can't find cert, log warning
        logger.warning("OrbStack detected but certificate not found")
        return None

    def _find_system_cert(self) -> Optional[str]:
        """Find system CA certificates."""
        for cert_path in self.SYSTEM_CERT_PATHS:
            path = Path(cert_path)
            if path.exists():
                return str(path)
        return None

    def get_ssl_context(self, verify: bool = True) -> Optional[ssl.SSLContext]:
        """
        Get configured SSL context for HTTPS connections.

        Args:
            verify: Whether to verify SSL certificates

        Returns:
            Configured SSL context or None if verification disabled
        """
        if not verify:
            return False  # httpx accepts False for no verification

        if self._ssl_context is None:
            if self._cert_path:
                try:
                    self._ssl_context = ssl.create_default_context(
                        cafile=self._cert_path
                    )
                    logger.debug(f"SSL context created with {self._cert_path}")
                except Exception as e:
                    logger.error(f"Failed to create SSL context: {e}")
                    # Fallback to default
                    self._ssl_context = ssl.create_default_context()
            else:
                self._ssl_context = ssl.create_default_context()

        return self._ssl_context

    def get_httpx_client(
        self, timeout: float = 30.0, verify: bool = True, **kwargs
    ) -> httpx.Client:
        """
        Get configured httpx client with proper SSL settings.

        Args:
            timeout: Request timeout in seconds
            verify: Whether to verify SSL certificates
            **kwargs: Additional httpx.Client arguments

        Returns:
            Configured httpx.Client instance
        """
        ssl_context = self.get_ssl_context(verify)

        client_args = {
            "timeout": timeout,
            "verify": ssl_context if verify else False,
            **kwargs,
        }

        return httpx.Client(**client_args)

    def get_async_httpx_client(
        self, timeout: float = 30.0, verify: bool = True, **kwargs
    ) -> httpx.AsyncClient:
        """
        Get configured async httpx client with proper SSL settings.

        Args:
            timeout: Request timeout in seconds
            verify: Whether to verify SSL certificates
            **kwargs: Additional httpx.AsyncClient arguments

        Returns:
            Configured httpx.AsyncClient instance
        """
        ssl_context = self.get_ssl_context(verify)

        client_args = {
            "timeout": timeout,
            "verify": ssl_context if verify else False,
            **kwargs,
        }

        return httpx.AsyncClient(**client_args)

    def validate_certificate(self, url: str) -> tuple[bool, str]:
        """
        Validate SSL certificate for a given URL.

        Args:
            url: URL to validate

        Returns:
            Tuple of (success, message)
        """
        try:
            client = self.get_httpx_client(timeout=5.0)
            response = client.head(url)
            response.raise_for_status()
            return True, f"Certificate valid for {url}"
        except httpx.ConnectError as e:
            if "certificate" in str(e).lower():
                return False, f"Certificate error: {e}"
            return False, f"Connection error: {e}"
        except Exception as e:
            return False, f"Validation failed: {e}"

    def get_info(self) -> dict:
        """
        Get information about current SSL configuration.

        Returns:
            Dictionary with configuration details
        """
        return {
            "environment": self._environment,
            "cert_path": self._cert_path,
            "cert_exists": Path(self._cert_path).exists() if self._cert_path else False,
            "is_orbstack": self._is_orbstack(),
            "env_vars": {
                "SSL_CERT_FILE": os.environ.get("SSL_CERT_FILE"),
                "SSL_CERT_DIR": os.environ.get("SSL_CERT_DIR"),
                "REQUESTS_CA_BUNDLE": os.environ.get("REQUESTS_CA_BUNDLE"),
            },
        }

    def __str__(self) -> str:
        """String representation of SSL configuration."""
        info = self.get_info()
        return (
            f"SSLConfig(environment={info['environment']}, "
            f"cert={info['cert_path']}, "
            f"exists={info['cert_exists']})"
        )


# Singleton instance
_ssl_config: Optional[SSLConfig] = None


def get_ssl_config() -> SSLConfig:
    """
    Get or create singleton SSL configuration instance.

    Returns:
        Configured SSLConfig instance
    """
    global _ssl_config
    if _ssl_config is None:
        _ssl_config = SSLConfig()
    return _ssl_config


def create_langfuse_httpx_client(timeout: float = 30.0) -> httpx.Client:
    """
    Create httpx client specifically configured for Langfuse.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Configured httpx.Client for Langfuse
    """
    config = get_ssl_config()
    return config.get_httpx_client(timeout=timeout)


if __name__ == "__main__":
    # Test SSL configuration
    import sys

    logging.basicConfig(level=logging.DEBUG)

    config = get_ssl_config()
    print(f"\n{config}\n")
    print("Configuration details:")
    for key, value in config.get_info().items():
        print(f"  {key}: {value}")

    # Test URL validation if provided
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"\nValidating {test_url}...")
        success, message = config.validate_certificate(test_url)
        print(f"  Result: {'✅' if success else '❌'} {message}")
