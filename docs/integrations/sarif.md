# SARIF & Code Scanning

Noxaudit can output findings in [SARIF](https://sarifweb.azurewebsites.net/) (Static Analysis Results Interchange Format), which integrates with GitHub Code Scanning to show findings as security alerts in your repository.

## Generating SARIF Output

Use the `--format sarif` flag:

```bash
noxaudit run --focus security --format sarif
```

SARIF files are saved to `.noxaudit/reports/{repo}/{date}-{focus}.sarif`.

## SARIF Format

Noxaudit generates SARIF 2.1.0 documents with:

- **Tool information**: Noxaudit name and version
- **Rules**: One rule per finding type with description and help text
- **Results**: Individual findings with file locations, severity, and fix suggestions
- **Fingerprints**: Stable identifiers for deduplication across runs

### Severity Mapping

| Noxaudit Severity | SARIF Level |
|-------------------|-------------|
| HIGH | `error` |
| MEDIUM | `warning` |
| LOW | `note` |

## GitHub Code Scanning

### Manual Upload

Upload SARIF results using the GitHub CLI:

```bash
noxaudit run --focus security --format sarif
gh api \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  /repos/OWNER/REPO/code-scanning/sarifs \
  -f "sarif=$(gzip -c .noxaudit/reports/my-app/*-security.sarif | base64)"
```

### GitHub Actions

Use the action's built-in SARIF upload:

```yaml
- uses: atriumn/noxaudit/action@main
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    output-format: sarif
    upload-sarif: true
```

Or use the standard `github/codeql-action/upload-sarif` action:

```yaml
- uses: atriumn/noxaudit/action@main
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    output-format: sarif

- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: .noxaudit/reports/
```

### Viewing Alerts

Once uploaded, findings appear in your repository's **Security** tab under **Code Scanning alerts**. Each alert shows:

- Severity level
- Affected file and line
- Finding description
- Suggested fix

Alerts persist across runs and are automatically closed when the finding is no longer reported.

## Batch Workflow

SARIF output also works with the submit/retrieve workflow:

```bash
noxaudit submit --focus security
# ... wait ...
noxaudit retrieve --format sarif
```

Or in GitHub Actions:

```yaml
- uses: atriumn/noxaudit/action@main
  with:
    mode: retrieve
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    output-format: sarif
    upload-sarif: true
```
