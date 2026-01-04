# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, report them through GitHub's private security advisory:

1. Go to [Security Advisories](https://github.com/devbyteai/ghoststorm/security/advisories/new)
2. Click "Report a vulnerability"
3. Fill out the form with details

### What to include

- Type of vulnerability
- Full paths of affected files
- Step-by-step instructions to reproduce
- Proof-of-concept or exploit code (if possible)
- Impact assessment

### Response Timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 7 days
- **Fix timeline**: Depends on severity

### After Reporting

1. We'll confirm receipt within 48 hours
2. We'll investigate and determine severity
3. We'll work on a fix
4. We'll coordinate disclosure timing with you
5. We'll credit you in the release notes (if desired)

## Security Best Practices

When using GhostStorm:

- Keep the software updated
- Use strong proxy credentials
- Don't expose the API publicly without authentication
- Review flow scripts before execution
- Use Docker for isolation

## Known Security Considerations

- **Proxy credentials**: Stored in config files; use environment variables in production
- **LLM API keys**: Stored locally; use secrets management in production
- **Browser automation**: Can execute arbitrary JavaScript; review flows carefully

## Contact

For security concerns: Open a private security advisory on GitHub.
