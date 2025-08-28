#!/usr/bin/env python3
"""
Langfuse Connection Health Check Script

Validates SSL certificate configuration, API connectivity, and Langfuse integration.
Provides detailed diagnostics for troubleshooting connection issues.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ssl_config import get_ssl_config, SSLConfig
from langfuse import Langfuse
import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LangfuseHealthCheck:
    """Comprehensive health check for Langfuse integration."""

    def __init__(self, verbose: bool = False):
        """Initialize health check with verbosity setting."""
        self.verbose = verbose
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        self.ssl_config = get_ssl_config()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "summary": {"passed": 0, "failed": 0, "warnings": 0},
        }

    def print_header(self, title: str):
        """Print formatted section header."""
        print(f"\n{'='*60}")
        print(f" {title}")
        print("=" * 60)

    def print_result(
        self, test: str, success: bool, message: str = "", warning: bool = False
    ):
        """Print test result with status indicator."""
        if warning:
            status = "⚠️  WARNING"
            self.results["summary"]["warnings"] += 1
        elif success:
            status = "✅ PASS"
            self.results["summary"]["passed"] += 1
        else:
            status = "❌ FAIL"
            self.results["summary"]["failed"] += 1

        print(f"{status:12} | {test:40} | {message}")

        self.results["checks"][test] = {
            "status": "pass" if success else "warn" if warning else "fail",
            "message": message,
        }

    def check_environment(self) -> bool:
        """Check environment variables and configuration."""
        self.print_header("Environment Configuration")

        all_good = True

        # Check SSL configuration
        ssl_info = self.ssl_config.get_info()
        self.print_result(
            "SSL Configuration",
            ssl_info["cert_exists"],
            f"{ssl_info['environment']} - {ssl_info['cert_path']}",
        )

        # Check for OrbStack
        if ssl_info["is_orbstack"]:
            self.print_result(
                "OrbStack Detection", True, "OrbStack environment detected"
            )

        # Check Langfuse host
        host = os.getenv("LANGFUSE_HOST")
        if host:
            self.print_result("LANGFUSE_HOST", True, host)
        else:
            self.print_result(
                "LANGFUSE_HOST", False, "Not configured (will use default)"
            )
            all_good = False

        # Check API keys
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")

        if public_key:
            masked = f"{public_key[:20]}..." if len(public_key) > 20 else public_key
            self.print_result("LANGFUSE_PUBLIC_KEY", True, masked)
        else:
            self.print_result("LANGFUSE_PUBLIC_KEY", False, "Not configured")
            all_good = False

        if secret_key:
            masked = f"{secret_key[:10]}..." if len(secret_key) > 10 else "***"
            self.print_result("LANGFUSE_SECRET_KEY", True, masked)
        else:
            self.print_result("LANGFUSE_SECRET_KEY", False, "Not configured")
            all_good = False

        return all_good

    def check_ssl_certificate(self) -> bool:
        """Validate SSL certificate for Langfuse host."""
        self.print_header("SSL Certificate Validation")

        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        # Remove path if present
        if host.startswith(("http://", "https://")):
            base_url = host.split("/")[0] + "//" + host.split("/")[2]
        else:
            base_url = f"https://{host}"

        success, message = self.ssl_config.validate_certificate(base_url)
        self.print_result(f"Certificate for {base_url}", success, message)

        if self.verbose and not success:
            print("\n  Debugging SSL issue:")
            print(f"  - Certificate path: {self.ssl_config._cert_path}")
            print(
                f"  - Certificate exists: {Path(self.ssl_config._cert_path).exists() if self.ssl_config._cert_path else False}"
            )
            print(f"  - Environment: {self.ssl_config._environment}")

        return success

    def check_api_connectivity(self) -> bool:
        """Test Langfuse API connectivity."""
        self.print_header("API Connectivity")

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not public_key or not secret_key:
            self.print_result("API Connection", False, "Missing credentials")
            return False

        try:
            # Create client with SSL configuration
            httpx_client = self.ssl_config.get_httpx_client(timeout=10.0)

            client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
                httpx_client=httpx_client,
            )

            # Try to list traces (with limit 1 to minimize data)
            result = client.api.trace.list(limit=1)

            self.print_result("API Authentication", True, "Successfully authenticated")

            # Check if we can access data
            if hasattr(result, "data"):
                trace_count = len(result.data)
                self.print_result("Data Access", True, f"Found {trace_count} trace(s)")

                if trace_count > 0 and self.verbose:
                    trace = result.data[0]
                    print(f"\n  Sample trace:")
                    print(f"    ID: {trace.id[:20]}...")
                    print(f"    Name: {trace.name}")
                    print(f"    Timestamp: {trace.timestamp}")

            return True

        except httpx.ConnectError as e:
            if "certificate" in str(e).lower():
                self.print_result(
                    "API Connection", False, f"SSL Certificate error: {e}"
                )
            else:
                self.print_result("API Connection", False, f"Connection error: {e}")
            return False

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Invalid credentials" in error_msg:
                self.print_result(
                    "API Authentication", False, "Invalid API credentials"
                )
            else:
                self.print_result("API Connection", False, f"Error: {e}")

            if self.verbose:
                import traceback

                print("\n  Full error trace:")
                traceback.print_exc()

            return False

    def check_1password_integration(self) -> bool:
        """Check if 1Password integration is working."""
        self.print_header("1Password Integration")

        try:
            # Check if op CLI is available
            result = subprocess.run(
                ["op", "--version"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                self.print_result("1Password CLI", True, f"Version: {version}")

                # Try to get Langfuse item
                result = subprocess.run(
                    [
                        "op",
                        "item",
                        "get",
                        "ctyxybforywkjp2krbdpeulzzq",
                        "--format",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    self.print_result(
                        "Langfuse Credentials", True, "Available in 1Password"
                    )
                    return True
                else:
                    self.print_result(
                        "Langfuse Credentials", False, "Cannot access item"
                    )
                    return False
            else:
                self.print_result(
                    "1Password CLI", False, "Not installed or not configured"
                )
                return False

        except subprocess.TimeoutExpired:
            self.print_result(
                "1Password CLI", False, "Timeout - may need authentication"
            )
            return False
        except FileNotFoundError:
            self.print_result("1Password CLI", False, "Not installed")
            return False

    def suggest_fixes(self):
        """Provide suggestions for failed checks."""
        self.print_header("Suggested Fixes")

        failed_checks = [
            k for k, v in self.results["checks"].items() if v["status"] == "fail"
        ]

        if not failed_checks:
            print("✨ All checks passed! No fixes needed.")
            return

        suggestions = {
            "SSL Configuration": [
                "1. Check if OrbStack certificate exists: ls -la /usr/local/share/ca-certificates/",
                "2. Set SSL_CERT_FILE environment variable to certificate path",
                "3. Update ca-certificates if running in container: update-ca-certificates",
            ],
            "LANGFUSE_HOST": [
                "1. Set LANGFUSE_HOST environment variable",
                "2. For OrbStack: export LANGFUSE_HOST=https://langfuse.local",
                "3. For internal Docker: export LANGFUSE_HOST=http://langfuse-web:3000",
            ],
            "LANGFUSE_PUBLIC_KEY": [
                "1. Get from 1Password: op item get ctyxybforywkjp2krbdpeulzzq",
                "2. Set environment variable: export LANGFUSE_PUBLIC_KEY=pk-lf-...",
            ],
            "LANGFUSE_SECRET_KEY": [
                "1. Get from 1Password: op item get ctyxybforywkjp2krbdpeulzzq",
                "2. Set environment variable: export LANGFUSE_SECRET_KEY=sk-lf-...",
            ],
            "API Authentication": [
                "1. Verify credentials are correct",
                "2. Check if host URL matches the Langfuse instance",
                "3. Ensure API keys have necessary permissions",
            ],
            "Certificate": [
                "1. For OrbStack, ensure certificate is trusted",
                "2. Export SSL_CERT_FILE=/usr/local/share/ca-certificates/orbstack-root.crt",
                "3. Or disable verification temporarily (not recommended): verify=False",
            ],
        }

        for check in failed_checks:
            for key, fixes in suggestions.items():
                if key.lower() in check.lower():
                    print(f"\n📌 Fix for '{check}':")
                    for fix in fixes:
                        print(f"   {fix}")
                    break

    def run_all_checks(self) -> bool:
        """Run all health checks and return overall status."""
        print("\n" + "=" * 60)
        print(" Langfuse Connection Health Check")
        print("=" * 60)
        print(f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" Verbose: {self.verbose}")

        # Run checks
        env_ok = self.check_environment()
        ssl_ok = self.check_ssl_certificate()
        api_ok = self.check_api_connectivity()
        op_ok = self.check_1password_integration()

        # Summary
        self.print_header("Summary")
        total = self.results["summary"]["passed"] + self.results["summary"]["failed"]
        print(f"Passed:   {self.results['summary']['passed']}/{total}")
        print(f"Failed:   {self.results['summary']['failed']}/{total}")
        print(f"Warnings: {self.results['summary']['warnings']}")

        all_passed = self.results["summary"]["failed"] == 0

        if all_passed:
            print("\n🎉 All health checks passed!")
        else:
            print("\n⚠️  Some health checks failed.")
            self.suggest_fixes()

        # Save results to file if verbose
        if self.verbose:
            results_file = Path("langfuse_health_check_results.json")
            with open(results_file, "w") as f:
                json.dump(self.results, f, indent=2)
            print(f"\nDetailed results saved to: {results_file}")

        return all_passed


def main():
    """Main entry point for health check script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check Langfuse connection health and SSL configuration"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output with debugging information",
    )
    parser.add_argument(
        "--fix", action="store_true", help="Show suggested fixes for any issues found"
    )

    args = parser.parse_args()

    # Run health check
    checker = LangfuseHealthCheck(verbose=args.verbose)
    success = checker.run_all_checks()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
