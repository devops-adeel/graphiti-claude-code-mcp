# Security Policy

## 🔒 Our Security Commitment

This project takes security seriously. We use multiple layers of protection to prevent sensitive data exposure and maintain secure coding practices.

## 🚨 Security Incident Response

### Immediate Actions for Exposed Secrets

If you discover exposed credentials in this repository:

1. **IMMEDIATELY ROTATE THE CREDENTIALS** (Within minutes, not hours)
   - Log into the affected service
   - Generate new API keys/credentials
   - Update 1Password vault with new values
   - Document the rotation in the incident log

2. **Assess the Exposure**
   - Check service logs for unauthorized access
   - Determine how long the credentials were exposed
   - Identify which systems had access to the exposed credentials

3. **Remediate the Code**
   - Remove hardcoded secrets from current files
   - Update to use environment variables or secret management
   - Consider if git history cleanup is needed

4. **Notify and Document**
   - Create a security incident ticket
   - Notify the team lead
   - Document lessons learned

### Git History Cleanup Decision Tree

```
Was the secret exposed in a PUBLIC repository?
├── YES: The secret is permanently compromised
│   ├── Was it a production secret?
│   │   ├── YES: CRITICAL - Rotate immediately, consider repository migration
│   │   └── NO: Rotate and focus on prevention
│   └── Consider: Accept history (it's already indexed) or create new repo
└── NO: Private repository
    ├── How many people have access?
    ├── Consider using git-filter-repo if the team is small
    └── Coordinate with all team members for cleanup
```

## 🛡️ Prevention Infrastructure

### 1. Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### 2. Secret Scanning Tools
- **TruffleHog**: Detects secrets in git history
- **Gitleaks**: Pattern-based secret detection
- **GitHub Secret Scanning**: Automatic detection and alerts

### 3. 1Password Integration
All secrets are stored in 1Password and injected at runtime. Never hardcode credentials.

## 📋 Security Checklist

### Before Committing
- [ ] Run `pre-commit run --all-files`
- [ ] Check for hardcoded credentials
- [ ] Verify .gitignore includes sensitive files
- [ ] Use environment variables for secrets

### During Code Review
- [ ] Check for hardcoded secrets
- [ ] Verify proper secret management
- [ ] Ensure logging doesn't expose secrets
- [ ] Validate input sanitization

### For New Developers
- [ ] Set up 1Password access
- [ ] Install pre-commit hooks
- [ ] Read this security policy
- [ ] Complete security training

## 🔑 Secret Management Best Practices

### DO ✅
- Use 1Password for all secrets
- Use environment variables in code
- Use placeholders in setup scripts
- Rotate credentials regularly (90 days)
- Use mock credentials in tests

### DON'T ❌
- Hardcode any credentials (even test ones)
- Log secrets or sensitive data
- Commit .env files with real values
- Share credentials via Slack/email
- Use production credentials in development

## 📊 Secret Types and Rotation Schedule

| Secret Type | Rotation Frequency | Storage Location | Risk Level |
|------------|-------------------|------------------|------------|
| API Keys | 90 days | 1Password | High |
| Service Tokens | 90 days | 1Password | High |
| Database Passwords | 180 days | 1Password | Critical |
| Test Credentials | Never (use mocks) | Code (as mocks) | Low |

## 🔍 Detection Patterns

Our security tools scan for:
- Langfuse API keys: `pk-lf-*`, `sk-lf-*`
- OpenAI API keys: `sk-*`
- 1Password tokens: `OP_SERVICE_ACCOUNT_TOKEN`
- Generic patterns: passwords, tokens, keys
- Database URLs with credentials

## 📚 Security Resources

### Internal Documentation
- [1Password Security Model](docs/1password-security.md)
- [README - Security Section](README.md#security)

### External Resources
- [GitHub: Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [git-filter-repo Documentation](https://github.com/newren/git-filter-repo)
- [TruffleHog Documentation](https://github.com/trufflesecurity/trufflehog)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

## 🚀 Quick Commands

```bash
# Scan for secrets locally
trufflehog git file://. --since-commit HEAD --fail

# Run gitleaks scan
gitleaks detect --config=.gitleaks.toml

# Check git history for specific string
git log -S"sensitive_string" --all

# Rotate Langfuse credentials in 1Password
op item edit "ctyxybforywkjp2krbdpeulzzq" --vault=HomeLab \
  "langfuse-public-key[text]=NEW_PUBLIC_KEY" \
  "langfuse-secret-key[password]=NEW_SECRET_KEY"
```

## 📞 Security Contacts

- **Security Lead**: [Configure in GitHub Settings]
- **Incident Response**: Create issue with `security` label
- **Emergency**: Use GitHub Security Advisory feature

## 🔄 Policy Updates

This security policy is reviewed quarterly and updated as needed. Last review: 2025-08-27

## 🏆 Security Acknowledgments

We appreciate responsible disclosure of security issues. If you find a security vulnerability:
1. Do NOT create a public issue
2. Use GitHub's Security Advisory feature
3. Or email the security contact directly

---

**Remember**: Security is everyone's responsibility. When in doubt, ask for help!
