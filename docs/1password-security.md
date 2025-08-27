# 1Password Security Configuration

## Security Model: Read-Only Service Account

This project uses a **read-only** Service Account for 1Password integration, following the principle of least privilege.

### Key Security Decisions

1. **Service Account Permissions**: `read_items` only
   - Can read secrets for runtime injection
   - Cannot modify, create, or delete secrets
   - Reduces attack surface if token is compromised

2. **Human-Only Write Access**: All secret modifications require:
   - Manual execution via `op` CLI
   - Touch ID authentication
   - Clear audit trail

### Current Configuration

- **Service Account**: "Graphiti MCP Server ReadOnly"
- **Permissions**: `HomeLab:read_items`
- **Expiry**: 90 days from creation
- **Token Location**: `~/.config/graphiti-mcp/service-token`

### How to Update Secrets

When you need to update a secret in 1Password:

```bash
# 1. Authenticate with Touch ID (required)
op signin

# 2. Update the specific field
# For OpenAI API key:
op item edit "37e5lxhox53xsvzp3ozau32nha" \
  --vault=HomeLab \
  "openai-api-key[concealed]=sk-proj-YOUR-NEW-KEY"

# For Langfuse credentials:
op item edit "ctyxybforywkjp2krbdpeulzzq" \
  --vault=HomeLab \
  "langfuse-public-key[text]=pk-lf-NEW-KEY" \
  "langfuse-secret-key[password]=sk-lf-NEW-KEY"

# 3. Rebuild and restart services
make rebuild-secure
```

### Security Benefits

✅ **Separation of Duties**: Automated systems read, humans write  
✅ **Audit Trail**: Every secret modification requires Touch ID  
✅ **Damage Limitation**: Compromised token can't corrupt secrets  
✅ **Compliance**: Follows security best practices for service accounts  

### Token Renewal

Service Account tokens expire after 90 days. To renew:

```bash
# Create new read-only Service Account
op service-account create "Graphiti MCP Server ReadOnly" \
  --vault "HomeLab:read_items" \
  --expires-in 90d

# Update token in ~/.config/graphiti-mcp/service-token
# Test with: make test-1password
```

### Emergency Access

If the Service Account token is lost or compromised:

1. Delete the compromised Service Account via 1Password UI
2. Create a new read-only Service Account
3. Update the token file
4. Restart all services

### Important Notes

- Never commit the service-token file to git
- Never grant write permissions to Service Accounts
- Always use Touch ID for secret modifications
- Monitor Service Account usage in 1Password audit logs