# Langfuse Deployment Storage Issue - September 2, 2025

## Problem Summary
Langfuse traces are not being stored in the database, preventing all observability features. Authentication works, traces are created locally, but the ingestion endpoint fails to persist them.

## Symptoms
- No traces stored since August 21, 2025
- Ingestion endpoint returns HTTP 500 errors
- Error message: "Failed to upload events to blob storage, aborting event processing"
- All 677 existing traces are from old API key: `pk-lf-00689068-[REDACTED]`
- New API key traces (`pk-lf-cbed6edc-[REDACTED]`) are not stored

## Root Cause
1. **Primary Issue**: S3/MinIO upload failures preventing trace storage
2. **Configuration Issue**: Environment variables not properly injected into Docker containers
3. **Authentication Issue**: API keys were generated for different host URL

## Investigation Results

### Database Status
```sql
-- PostgreSQL: No traces in main database
SELECT COUNT(*) FROM traces WHERE project_id = 'cme5iapbq0005mi07dexij588';
-- Result: 0

-- ClickHouse: All traces are old (August 21)
SELECT COUNT(*), MAX(timestamp) FROM traces WHERE project_id = 'cme5iapbq0005mi07dexij588';
-- Result: 677, 2025-08-21 23:25:30.446
```

### API Key Verification
```sql
-- Current API key is correctly associated with project
SELECT * FROM api_keys WHERE public_key LIKE 'pk-lf-cbed6edc%';
-- Result: Correctly linked to project_id = 'cme5iapbq0005mi07dexij588'
```

### Error Logs
```javascript
// From docker logs langfuse-prod-langfuse-web-1
2025-09-02T20:32:14.563Z error: Failed to upload event to S3
Error: Failed to upload events to blob storage, aborting event processing
    at /app/web/.next/server/chunks/9600.js:25:5248
```

## Solution Steps

### 1. Fix Deployment Configuration
```bash
# Navigate to deployment directory
cd ../langfuse-deployment

# Deploy with proper secret injection from 1Password
make deploy

# This command:
# - Injects secrets from 1Password
# - Restarts all services with correct environment variables
# - Verifies health checks pass
```

### 2. Generate Fresh API Keys
```bash
# Store in 1Password vault: HomeLab
# Item: Langfusev3
# Fields: public-key, secret-key, host
# Host value: https://langfuse.local
```

### 3. Configure Application
```bash
# Create .env file with 1Password references
cat > .env << 'EOF'
# Langfuse Configuration - Using 1Password for secure credential management
LANGFUSE_PUBLIC_KEY=op://HomeLab/Langfusev3/public-key
LANGFUSE_SECRET_KEY=op://HomeLab/Langfusev3/secret-key
LANGFUSE_HOST=op://HomeLab/Langfusev3/host
LANGFUSE_ENABLED=true
OTEL_EXPORTER_OTLP_INSECURE=true  # Required for self-signed certificates
EOF
```

## Verification Steps

### Test Trace Creation
```python
# Test with: op run --env-file=".env" -- python3 test_simple_trace.py
import httpx
from langfuse import Langfuse

httpx_client = httpx.Client(verify=False)  # Required for self-signed certs
langfuse = Langfuse(
    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    host=os.environ.get("LANGFUSE_HOST"),
    httpx_client=httpx_client
)

# Create trace
with langfuse.start_as_current_span(name="test_trace") as span:
    trace_id = langfuse.get_current_trace_id()
    print(f"Created trace: {trace_id}")

langfuse.flush()
```

### Check Storage
```bash
# Verify trace is stored in ClickHouse
docker exec langfuse-prod-clickhouse-1 clickhouse-client --query \
  "SELECT id, timestamp FROM traces WHERE id = '<trace_id>';"
```

## Current Status
- ✅ Authentication working
- ✅ Traces created locally
- ✅ API keys correctly configured
- ❌ S3/MinIO upload failing
- ❌ Traces not persisted to database
- ❌ OTEL exporter SSL warnings (non-blocking)

## Next Steps
1. Fix MinIO bucket permissions
2. Verify S3 credentials in environment
3. Test ingestion endpoint directly
4. Monitor for successful trace storage

## Related Files
- `.env` - Environment configuration with 1Password references
- `../langfuse-deployment/compose/docker-compose.yml` - Deployment configuration
- `../langfuse-deployment/secrets/.env.1password.core` - Secret templates

## Commands Reference
```bash
# Check service health
docker ps | grep langfuse

# View logs
docker logs langfuse-prod-langfuse-web-1 --tail 50

# Check environment variables
docker exec langfuse-prod-langfuse-web-1 env | grep -E "S3|MINIO"

# Restart services
cd ../langfuse-deployment && make deploy
```
