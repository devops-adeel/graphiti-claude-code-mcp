# Security Configuration Reference

## Overview

This reference documents all security configurations and best practices for the Graphiti Claude Code MCP server.

## 1Password SDK Integration

### Configuration

The system uses 1Password SDK for runtime secret retrieval:

```bash
# Service account token location
~/.config/graphiti-mcp/service-token

# Required vault access
Vault: HomeLab
Items: FalkorDB/Integration, Langfuse/Integration
```

### Secret References

All secrets are defined in `config/secrets_manifest.py`:

| Secret | 1Password Item | Field | Usage |
|--------|---------------|-------|-------|
| `OPENAI_API_KEY` | FalkorDB/Integration | api_key | LLM operations |
| `LANGFUSE_PUBLIC_KEY` | Langfuse/Integration | public_key | Tracing |
| `LANGFUSE_SECRET_KEY` | Langfuse/Integration | secret_key | Tracing auth |
| `LANGFUSE_HOST` | Langfuse/Integration | host | API endpoint |

### Health Monitoring

```python
# Check token expiration
from config.secrets_manager import SecretsManager
manager = SecretsManager()
health = await manager.check_health()
print(f"Token expires: {health['token_expiry']}")
```

## Pre-commit Security Hooks

### Configuration

`.pre-commit-config.yaml` includes:

```yaml
repos:
  - repo: https://github.com/trufflesecurity/trufflehog
    hooks:
      - id: trufflehog
        args: ['--no-update', '--fail']

  - repo: https://github.com/gitleaks/gitleaks
    hooks:
      - id: gitleaks
```

### Running Security Scans

```bash
# Install hooks (required)
pre-commit install

# Manual scan
pre-commit run --all-files

# Skip hooks temporarily (emergency only)
SKIP=gitleaks,trufflehog git commit -m "message"
```

## Environment Variables

### Required Configuration

Store in `~/.config/graphiti-mcp/.env.graphiti`:

```bash
# FalkorDB Connection (non-secret)
FALKORDB_HOST=falkordb.local
FALKORDB_PORT=6379
FALKORDB_DATABASE=shared_knowledge

# Graphiti Configuration (non-secret)
GRAPHITI_GROUP_ID=shared_knowledge
GRAPHITI_BATCH_SIZE=50
MEMORY_DECAY_FACTOR=0.95

# Feature Flags (non-secret)
ENABLE_GTD_INTEGRATION=true
ENABLE_CROSS_REFERENCES=true
```

### Runtime Secrets

Retrieved from 1Password at runtime:

```python
# DO NOT hardcode these
OPENAI_API_KEY        # From 1Password
LANGFUSE_PUBLIC_KEY   # From 1Password
LANGFUSE_SECRET_KEY   # From 1Password
```

## Docker Security

### Build-time Security

```dockerfile
# No secrets in Dockerfile
# Use runtime injection
ENV OP_SERVICE_ACCOUNT_TOKEN=""

# Run as non-root user
USER appuser
```

### Runtime Security

```bash
# Mount token as read-only
docker run -v ~/.config/graphiti-mcp/service-token:/app/token:ro

# Network isolation
--network graphiti-network

# Resource limits
--memory="2g" --cpus="1.5"
```

## SSL/TLS Configuration

### OrbStack HTTPS

```python
# Certificate location
SSL_CERT_FILE=/tmp/orbstack-root.crt

# httpx configuration
import httpx
client = httpx.Client(
    verify="/tmp/orbstack-root.crt",
    timeout=30.0
)
```

### Production TLS

```python
# Enforce TLS 1.2+
import ssl
context = ssl.create_default_context()
context.minimum_version = ssl.TLSVersion.TLSv1_2
```

## API Security

### Authentication

```python
# 1Password SDK handles auth
from config.secrets_manager import SecretsManager
manager = SecretsManager()
api_key = await manager.get_secret("OPENAI_API_KEY")
```

### Rate Limiting

```python
# Token limits
MAX_TOKENS = 7000  # Per request
BATCH_SIZE = 50    # Episodes per flush
```

### Input Validation

```python
# Escape special characters for FalkorDB
def escape_for_search(query: str) -> str:
    query = query.replace("@", "")
    query = query.replace(":", " ")
    return query
```

## Audit Logging

### Security Events

Log these events:

- Secret retrieval attempts
- Authentication failures
- SSL certificate errors
- Token expiration warnings

### Log Format

```python
logger.info(f"Secret retrieved: {secret_name[:4]}***")
logger.error(f"Auth failed: {error}")
logger.warning(f"Token expires in {days} days")
```

## Security Checklist

### Development

- [ ] Pre-commit hooks installed
- [ ] No hardcoded secrets
- [ ] 1Password SDK configured
- [ ] SSL certificates valid

### Deployment

- [ ] Service account token secured (600 permissions)
- [ ] Docker running as non-root
- [ ] Network isolation configured
- [ ] Resource limits set

### Monitoring

- [ ] Token expiration tracking
- [ ] Secret rotation schedule (90 days)
- [ ] Audit logs configured
- [ ] Security scan in CI/CD

## Incident Response

### If Secret Exposed

1. **Immediate**: Rotate affected credential
2. **Document**: Record in security log
3. **Scan**: Run full repository scan
4. **Review**: Check git history for exposure

### Security Contact

Report security issues via GitHub Security Advisory (not public issues).
