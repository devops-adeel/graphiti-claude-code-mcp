# SSL Certificate Troubleshooting Guide

## Overview

This guide helps troubleshoot SSL certificate issues when connecting to Langfuse or other HTTPS services in OrbStack, Docker, and cloud environments.

## Quick Diagnosis

Run the health check to identify SSL issues:

```bash
make langfuse-health-verbose
```

## Common SSL Errors and Solutions

### Error: `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain`

This is the most common error when using OrbStack with self-signed certificates.

#### Solution 1: Extract and Use OrbStack Certificate

1. Extract the certificate from a running container:
```bash
docker exec langfuse-prod-langfuse-web-1 cat /usr/local/share/ca-certificates/orbstack-root.crt > /tmp/orbstack-root.crt
```

2. Set environment variable:
```bash
export SSL_CERT_FILE=/tmp/orbstack-root.crt
```

3. Test the connection:
```bash
make test-langfuse-local
```

#### Solution 2: Use HTTP Instead of HTTPS

For internal Docker networks, use HTTP to avoid SSL issues:

```bash
export LANGFUSE_HOST=http://langfuse-web:3000
```

#### Solution 3: Configure httpx Client Properly

In Python code, explicitly configure the SSL context:

```python
import ssl
import httpx
from langfuse import Langfuse

# Create SSL context with OrbStack certificate
ssl_context = ssl.create_default_context(cafile='/tmp/orbstack-root.crt')
httpx_client = httpx.Client(verify=ssl_context)

client = Langfuse(
    public_key="...",
    secret_key="...",
    host="https://langfuse.local",
    httpx_client=httpx_client
)
```

## Environment-Specific Configuration

### OrbStack on macOS

OrbStack uses self-signed certificates for `.local` domains. The certificate is automatically added to containers but not to the host system.

**Inside Containers:**
- Certificate location: `/usr/local/share/ca-certificates/orbstack-root.crt`
- Environment: `SSL_CERT_FILE=/usr/local/share/ca-certificates/orbstack-root.crt`

**On Host (macOS):**
- Extract certificate from container (see Solution 1 above)
- Or disable SSL verification (development only)

### Standard Docker

Use HTTP for internal communication:

```bash
export LANGFUSE_HOST=http://langfuse-web:3000
```

### Cloud Deployments

Should work with standard SSL certificates:

```bash
export LANGFUSE_HOST=https://cloud.langfuse.com
```

## Diagnostic Commands

### Check SSL Configuration

```bash
# View current SSL configuration
make ssl-check

# Test certificate validation
python ssl_config.py https://langfuse.local

# Check if certificate exists
ls -la /usr/local/share/ca-certificates/orbstack-root.crt
```

### Test Langfuse Connection

```bash
# Test from host
make test-langfuse-local

# Test from Docker container
make test-langfuse-docker

# Run full health check
make langfuse-health-verbose
```

### Debug SSL Issues

```python
# Python script to debug SSL
import ssl
import httpx

# Test without verification (insecure)
response = httpx.get("https://langfuse.local", verify=False)
print(f"Status: {response.status_code}")

# Test with custom certificate
ssl_context = ssl.create_default_context(cafile="/tmp/orbstack-root.crt")
response = httpx.get("https://langfuse.local", verify=ssl_context)
print(f"Status: {response.status_code}")
```

## Environment Variables

### Required for Langfuse

```bash
# API Credentials (get from 1Password)
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...

# Host Configuration
export LANGFUSE_HOST=https://langfuse.local  # For OrbStack
# OR
export LANGFUSE_HOST=http://langfuse-web:3000  # For Docker internal

# SSL Certificate (for OrbStack)
export SSL_CERT_FILE=/tmp/orbstack-root.crt
export REQUESTS_CA_BUNDLE=/tmp/orbstack-root.crt
```

### Get Credentials from 1Password

```bash
# Get public key
op item get ctyxybforywkjp2krbdpeulzzq --fields "Langfuse.langfuse-public-key"

# Get secret key
op item get ctyxybforywkjp2krbdpeulzzq --fields "Langfuse.langfuse-secret-key"
```

## Automated Fixes

### Apply All SSL Fixes

```bash
# Show SSL fix commands
make fix-ssl

# Extract certificate and set environment
docker exec langfuse-prod-langfuse-web-1 cat /usr/local/share/ca-certificates/orbstack-root.crt > /tmp/orbstack-root.crt
export SSL_CERT_FILE=/tmp/orbstack-root.crt
export LANGFUSE_HOST=https://langfuse.local
```

## Network Connectivity Issues

### Container Cannot Reach Langfuse

1. Check Docker network:
```bash
docker network ls
docker inspect graphiti-claude-code-mcp | grep NetworkMode
```

2. Ensure containers are on same network:
```bash
# For Langfuse network
docker run --network langfuse-prod_default ...

# For shared OrbStack network
docker run --network orbstack-shared ...
```

### DNS Resolution Issues

Test DNS resolution:

```bash
# From container
docker exec exciting_feynman nslookup langfuse.local
docker exec exciting_feynman ping langfuse.local

# Check /etc/hosts
docker exec exciting_feynman cat /etc/hosts | grep langfuse
```

## Prevention Strategies

### 1. Use Environment-Specific Profiles

Configure different profiles for each environment:
- `config/environments/orbstack.yml` - OrbStack with SSL
- `config/environments/docker.yml` - Docker with HTTP
- `config/environments/cloud.yml` - Cloud with HTTPS

### 2. Auto-Detection in Code

The `ssl_config.py` module automatically detects the environment and configures SSL appropriately:

```python
from ssl_config import get_ssl_config, create_langfuse_httpx_client

# Automatically configured for your environment
httpx_client = create_langfuse_httpx_client()
```

### 3. Startup Validation

Always validate connections on startup:

```python
# In your application startup
from scripts.health_check_langfuse import LangfuseHealthCheck

checker = LangfuseHealthCheck(verbose=True)
if not checker.run_all_checks():
    print("Warning: Langfuse connection issues detected")
    checker.suggest_fixes()
```

## Security Considerations

⚠️ **Warning**: Never disable SSL verification in production!

**Development Only:**
```python
# INSECURE - Development only
httpx.Client(verify=False)
```

**Production:**
- Always use proper SSL certificates
- Validate certificate chains
- Use environment variables for sensitive data
- Store credentials in 1Password or secure vaults

## Troubleshooting Checklist

- [ ] SSL certificate exists at expected location
- [ ] Environment variables are set correctly
- [ ] Containers are on the correct Docker network
- [ ] API credentials are valid
- [ ] Host URL matches the Langfuse instance
- [ ] httpx client is configured with SSL context
- [ ] No firewall blocking connections
- [ ] DNS resolution working correctly

## Getting Help

If you're still experiencing issues:

1. Run the verbose health check:
   ```bash
   make langfuse-health-verbose
   ```

2. Check the logs:
   ```bash
   docker logs graphiti-claude-code-mcp
   ```

3. Test with the debug script:
   ```bash
   python scripts/health_check_langfuse.py --verbose
   ```

4. Review the generated health check results:
   ```bash
   cat langfuse_health_check_results.json
   ```

## Related Documentation

- [OrbStack HTTPS Documentation](https://docs.orbstack.dev/features/https)
- [Langfuse Python SDK](https://github.com/langfuse/langfuse-python)
- [httpx SSL Configuration](https://www.python-httpx.org/advanced/ssl/)
