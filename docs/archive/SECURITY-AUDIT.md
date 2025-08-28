# Security Audit Configuration

## Overview

This project uses **pip-audit** for Python dependency security scanning as part of the pre-commit hooks. pip-audit was chosen over safety for several key advantages.

## Why pip-audit?

### 1. Native pyproject.toml Support
- **pip-audit**: Built-in support for modern Python packaging standards
- **safety**: Primarily focused on requirements.txt files
- **Result**: No more conflicts between pyproject.toml and requirements.txt

### 2. Open Source Database
- **pip-audit**: Uses the transparent Python Packaging Advisory Database (PyPA)
- **safety**: Requires paid plan for full vulnerability database access
- **Result**: Complete security coverage without commercial restrictions

### 3. Active Maintenance
- Maintained by PyPA (Python Packaging Authority)
- Support from Trail of Bits and Google
- Regular updates and community involvement

### 4. Flexible Configuration
- Supports multiple input formats simultaneously
- Can audit installed environments, requirements files, or project directories
- Provides detailed vulnerability descriptions and fix recommendations

## Configuration

The security audit is configured in `.pre-commit-config.yaml`:

```yaml
# Security audit for Python dependencies using pip-audit
- repo: https://github.com/pypa/pip-audit
  rev: v2.9.0
  hooks:
    - id: pip-audit
      description: Check Python dependencies for known security vulnerabilities
      args: ["--desc", "--fix", "--dry-run"]
```

### Configuration Options

- `--desc`: Include detailed vulnerability descriptions
- `--fix`: Show which packages would be upgraded (dry-run mode prevents actual changes)
- `--dry-run`: Simulate the audit without making changes

## Dependency Synchronization

To handle both pyproject.toml and requirements.txt, we use an automated sync script:

```yaml
# Sync dependencies from pyproject.toml to requirements.txt
- repo: local
  hooks:
    - id: sync-dependencies
      name: Sync dependencies
      entry: python3 scripts/sync-dependencies.py
```

This ensures:
- Single source of truth in pyproject.toml
- Automatic generation of requirements.txt
- No manual synchronization needed
- Compatibility with all tools

## Usage

### Manual Security Audit
```bash
# Run security audit on current environment
pip-audit

# Audit with detailed descriptions
pip-audit --desc

# Audit and show potential fixes (dry-run)
pip-audit --fix --dry-run

# Audit requirements file
pip-audit -r requirements.txt

# Audit pyproject.toml
pip-audit .
```

### Pre-commit Integration
```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run only security audit
pre-commit run pip-audit
```

### CI/CD Integration
For GitHub Actions, pip-audit is automatically skipped in pre-commit.ci as it requires network access:

```yaml
ci:
  skip: [pip-audit]  # pre-commit.ci doesn't allow network calls
```

For proper CI security scanning, use the dedicated GitHub Action:

```yaml
- uses: pypa/gh-action-pip-audit@v1.0.0
  with:
    inputs: requirements.txt
```

## Handling Vulnerabilities

### When Vulnerabilities Are Found

1. **Review the Report**: pip-audit provides detailed descriptions and fix versions
2. **Update Dependencies**: Use the suggested fix versions
3. **Test Thoroughly**: Ensure updates don't break functionality
4. **Document Changes**: Update CHANGELOG.md with security fixes

### Ignoring False Positives

If a vulnerability is not applicable to your use case:

```bash
# Ignore specific vulnerability
pip-audit --ignore-vuln GHSA-xxxx-xxxx-xxxx

# Multiple ignores
pip-audit --ignore-vuln CVE-2025-XXXX --ignore-vuln CVE-2025-YYYY
```

## Best Practices

1. **Run Regularly**: Security audits should run on every commit via pre-commit
2. **Keep Updated**: Regularly update pip-audit to latest version
3. **Monitor Alerts**: Set up GitHub Dependabot for additional coverage
4. **Document Exceptions**: If vulnerabilities must be ignored, document why
5. **Layer Security**: Use multiple tools (TruffleHog, Gitleaks, pip-audit)

## Troubleshooting

### Common Issues

#### "Dependency not found on PyPI"
- Local packages (like this project) can't be audited
- This is expected and safe to ignore

#### Network Errors
- pip-audit requires internet access to check vulnerability databases
- Ensure proxy/firewall settings allow access to PyPI

#### Version Conflicts
- Run `python3 scripts/sync-dependencies.py` to sync dependencies
- Use `pip-audit --fix` to see suggested updates

## Migration from Safety

If migrating from safety to pip-audit:

1. Remove safety configuration from pre-commit
2. Add pip-audit configuration
3. Install pip-audit: `pip install pip-audit`
4. Test with: `pre-commit run pip-audit --all-files`

## Additional Resources

- [pip-audit Documentation](https://github.com/pypa/pip-audit)
- [Python Advisory Database](https://github.com/pypa/advisory-database)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Security Best Practices](https://owasp.org/www-project-top-ten/)
