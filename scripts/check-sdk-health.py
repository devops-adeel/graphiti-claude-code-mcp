#!/usr/bin/env python3
"""
1Password SDK Health Check Script

This script performs a comprehensive health check of the 1Password SDK integration,
including token validation, secret access, and system diagnostics.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from secrets_manager import SecretsManager


class HealthChecker:
    """Comprehensive health checker for 1Password SDK integration"""

    def __init__(self):
        self.checks = {
            "token_loaded": False,
            "token_valid": False,
            "token_format_ok": False,
            "sdk_initialized": False,
            "secrets_accessible": False,
            "cache_working": False,
            "token_days_left": 0,
            "environment_setup": False,
            "neo4j_config": False,
        }
        self.errors = []
        self.warnings = []

    async def run_all_checks(self):
        """Run all health checks"""
        print("🔍 1Password SDK Health Check")
        print("=" * 50)

        # Check 1: Token Loading
        await self.check_token_loading()

        # Check 2: SDK Initialization
        await self.check_sdk_initialization()

        # Check 3: Secret Access
        await self.check_secret_access()

        # Check 4: Cache Functionality
        await self.check_cache()

        # Check 5: Environment Setup
        await self.check_environment()

        # Check 6: Neo4j Configuration
        await self.check_neo4j_config()

        # Print summary
        self.print_summary()

        # Return exit code
        return 0 if all(self.checks.values()) else 1

    async def check_token_loading(self):
        """Check if token can be loaded"""
        print("\n1️⃣ Checking Token Loading...")

        try:
            # Try environment variable
            token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")

            if not token:
                # Try file
                token_file = Path("~/.config/graphiti-mcp/service-token").expanduser()
                if token_file.exists():
                    content = token_file.read_text()
                    for line in content.split("\n"):
                        if "export OP_SERVICE_ACCOUNT_TOKEN=" in line:
                            token = line.split("=", 1)[1].strip("'\"")
                            break
                    print(f"   ✅ Token loaded from file: {token_file}")
                else:
                    print(f"   ❌ Token file not found: {token_file}")
            else:
                print("   ✅ Token loaded from environment variable")

            if token:
                self.checks["token_loaded"] = True

                # Check format
                if token.startswith("ops_"):
                    self.checks["token_format_ok"] = True
                    print(f"   ✅ Token format valid (starts with 'ops_')")
                else:
                    print(f"   ⚠️ Token format suspicious (doesn't start with 'ops_')")
                    self.warnings.append("Token format may be invalid")

                # Check expiration
                created = datetime(2025, 8, 27)
                expires = created + timedelta(days=90)
                days_left = (expires - datetime.now()).days
                self.checks["token_days_left"] = days_left

                if days_left < 0:
                    print(f"   ❌ Token expired {abs(days_left)} days ago!")
                    self.errors.append(f"Token expired {abs(days_left)} days ago")
                elif days_left < 7:
                    print(f"   ⚠️ Token expires in {days_left} days!")
                    self.warnings.append(f"Token expires in {days_left} days")
                elif days_left < 30:
                    print(f"   📅 Token expires in {days_left} days")
                else:
                    print(f"   ✅ Token valid for {days_left} more days")
                    self.checks["token_valid"] = True
            else:
                print("   ❌ No token found")
                self.errors.append("No service account token found")

        except Exception as e:
            print(f"   ❌ Error checking token: {e}")
            self.errors.append(f"Token check error: {e}")

    async def check_sdk_initialization(self):
        """Check if SDK can initialize"""
        print("\n2️⃣ Checking SDK Initialization...")

        if not self.checks["token_loaded"]:
            print("   ⏭️ Skipping (no token)")
            return

        try:
            manager = await SecretsManager.get_instance()
            if manager._initialized:
                self.checks["sdk_initialized"] = True
                print("   ✅ SDK initialized successfully")
            else:
                print("   ❌ SDK failed to initialize")
                self.errors.append("SDK initialization failed")

        except Exception as e:
            print(f"   ❌ Error initializing SDK: {e}")
            self.errors.append(f"SDK init error: {e}")

    async def check_secret_access(self):
        """Check if secrets can be accessed"""
        print("\n3️⃣ Checking Secret Access...")

        if not self.checks["sdk_initialized"]:
            print("   ⏭️ Skipping (SDK not initialized)")
            return

        try:
            manager = await SecretsManager.get_instance()

            # Try to get a critical secret
            api_key = await manager.get_secret("OPENAI_API_KEY")

            if api_key and len(api_key) > 10:
                self.checks["secrets_accessible"] = True
                print(f"   ✅ Secrets accessible (OPENAI_API_KEY: {api_key[:10]}...)")

                # Check other secrets
                secrets_to_check = [
                    "LANGFUSE_PUBLIC_KEY",
                    "LANGFUSE_SECRET_KEY",
                    "LANGFUSE_HOST",
                ]

                for secret_name in secrets_to_check:
                    try:
                        value = await manager.get_secret(secret_name)
                        if value:
                            print(f"   ✅ {secret_name}: {'*' * 8}")
                        else:
                            print(f"   ⚠️ {secret_name}: Empty")
                            self.warnings.append(f"{secret_name} is empty")
                    except Exception as e:
                        print(f"   ❌ {secret_name}: {e}")
                        self.errors.append(f"Cannot access {secret_name}")
            else:
                print("   ❌ Secret retrieval failed or returned empty")
                self.errors.append("Secret retrieval failed")

        except Exception as e:
            print(f"   ❌ Error accessing secrets: {e}")
            self.errors.append(f"Secret access error: {e}")

    async def check_cache(self):
        """Check if caching is working"""
        print("\n4️⃣ Checking Cache Functionality...")

        if not self.checks["secrets_accessible"]:
            print("   ⏭️ Skipping (secrets not accessible)")
            return

        try:
            import time

            manager = await SecretsManager.get_instance()

            # Clear cache first
            manager.clear_cache()

            # First call
            start1 = time.time()
            value1 = await manager.get_secret("OPENAI_API_KEY")
            time1 = time.time() - start1

            # Second call (should be cached)
            start2 = time.time()
            value2 = await manager.get_secret("OPENAI_API_KEY")
            time2 = time.time() - start2

            if value1 == value2 and time2 < time1:
                self.checks["cache_working"] = True
                speedup = time1 / time2 if time2 > 0 else 999
                print(f"   ✅ Cache working ({speedup:.1f}x speedup)")
            else:
                print("   ⚠️ Cache may not be working optimally")
                self.warnings.append("Cache performance suboptimal")

        except Exception as e:
            print(f"   ❌ Error testing cache: {e}")
            self.errors.append(f"Cache test error: {e}")

    async def check_environment(self):
        """Check environment setup"""
        print("\n5️⃣ Checking Environment Setup...")

        required_vars = [
            "OPENAI_API_KEY",
            "GRAPHITI_GROUP_ID",
            "NEO4J_HOST",
            "NEO4J_PORT",
        ]

        all_set = True
        for var in required_vars:
            value = os.getenv(var)
            if value:
                if "KEY" in var or "SECRET" in var:
                    print(f"   ✅ {var}: {'*' * 8}")
                else:
                    print(f"   ✅ {var}: {value}")
            else:
                print(f"   ❌ {var}: Not set")
                all_set = False
                self.errors.append(f"{var} not in environment")

        self.checks["environment_setup"] = all_set

    async def check_neo4j_config(self):
        """Check Neo4j configuration"""
        print("\n6️⃣ Checking Neo4j Configuration...")
        # AI-CONTEXT: Neo4j graph database via OrbStack domain
        # Connection: bolt://neo4j.graphiti.local:7687
        # Database: "neo4j" (Community Edition requirement)

        host = os.getenv("NEO4J_HOST", "not set")
        port = os.getenv("NEO4J_PORT", "not set")
        database = os.getenv("NEO4J_DATABASE", "not set")
        group_id = os.getenv("GRAPHITI_GROUP_ID", "not set")

        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Database: {database}")
        print(f"   Group ID: {group_id}")

        # Check connectivity
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)

            # Try different host resolutions for OrbStack
            hosts_to_try = []
            if host == "neo4j.graphiti.local":
                hosts_to_try = ["neo4j.graphiti.local", "localhost", "127.0.0.1"]
            elif host == "host.docker.internal":
                hosts_to_try = ["localhost", "127.0.0.1"]
            else:
                hosts_to_try = [host]

            connected = False
            for test_host in hosts_to_try:
                try:
                    result = sock.connect_ex((test_host, int(port)))
                    if result == 0:
                        print(f"   ✅ Neo4j reachable at {test_host}:{port}")
                        connected = True
                        break
                except:
                    pass

            if not connected:
                print(f"   ⚠️ Cannot connect to Neo4j at {host}:{port}")
                self.warnings.append(f"Neo4j not reachable at {host}:{port}")

            self.checks["neo4j_config"] = connected
            sock.close()

        except Exception as e:
            print(f"   ❌ Error checking Neo4j: {e}")
            self.errors.append(f"Neo4j check error: {e}")

    def print_summary(self):
        """Print summary of health checks"""
        print("\n" + "=" * 50)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 50)

        # Status counts
        passed = sum(1 for v in self.checks.values() if v)
        total = len(self.checks)

        # Overall status
        if passed == total:
            print("✅ All checks passed!")
        elif passed > total / 2:
            print(f"⚠️ Partial success: {passed}/{total} checks passed")
        else:
            print(f"❌ Health check failed: {passed}/{total} checks passed")

        # Detailed results
        print("\nDetailed Results:")
        for check, status in self.checks.items():
            if check == "token_days_left":
                continue  # Skip numeric value
            emoji = "✅" if status else "❌"
            print(f"  {emoji} {check.replace('_', ' ').title()}: {status}")

        # Token expiry
        if self.checks["token_loaded"]:
            days = self.checks["token_days_left"]
            if days > 30:
                emoji = "✅"
            elif days > 7:
                emoji = "📅"
            elif days > 0:
                emoji = "⚠️"
            else:
                emoji = "❌"
            print(f"  {emoji} Token expires in: {days} days")

        # Warnings
        if self.warnings:
            print("\n⚠️ Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")

        # Errors
        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"  - {error}")

        # Recommendations
        if self.errors or self.warnings:
            print("\n💡 Recommendations:")

            if not self.checks["token_loaded"]:
                print("  1. Set OP_SERVICE_ACCOUNT_TOKEN environment variable")
                print("     Or ensure ~/.config/graphiti-mcp/service-token exists")

            if self.checks["token_days_left"] < 30:
                print("  2. Rotate service account token in 1Password soon")

            if not self.checks.get("neo4j_config", False):
                print("  3. Ensure Neo4j is running on the configured port")
                print("     Check with: docker ps | grep falkor")

            if not self.checks["secrets_accessible"]:
                print("  4. Verify vault permissions for the service account")
                print("     The account needs read access to HomeLab vault")


async def main():
    """Run health check"""
    checker = HealthChecker()
    exit_code = await checker.run_all_checks()

    print("\n" + "=" * 50)
    if exit_code == 0:
        print("✅ System is healthy and ready!")
    else:
        print("❌ Issues detected. Please address the errors above.")

    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
