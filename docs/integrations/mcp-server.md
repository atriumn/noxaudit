# MCP Server

Noxaudit includes a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that exposes audit data to AI coding tools like Claude Code, Cursor, and Windsurf.

## Installation

Install with the MCP extra:

```bash
pip install 'noxaudit[mcp]'
```

## Starting the Server

```bash
noxaudit mcp-server
```

The server runs over stdio and is designed to be launched by your AI coding tool.

## Configuring in AI Coding Tools

### Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "noxaudit": {
      "command": "noxaudit",
      "args": ["mcp-server"]
    }
  }
}
```

### Cursor / Windsurf

Add to your MCP configuration:

```json
{
  "noxaudit": {
    "command": "noxaudit",
    "args": ["mcp-server"]
  }
}
```

## Available Tools

The MCP server exposes 5 tools:

### `get_findings`

Query findings from the latest audit with optional filters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | string | Filter by file path (substring match) |
| `severity` | string | Filter by severity: `low`, `medium`, or `high` |
| `focus` | string | Filter by focus area |
| `limit` | int | Maximum number of findings to return |

**Example**: "Show me all high-severity security findings in auth.py"

### `get_health_summary`

Get a repository health score (0-100) with a breakdown of findings by severity and focus area.

No parameters required.

**Example**: "What's the health score for this repo?"

### `get_findings_for_diff`

Find audit findings that apply to files with uncommitted changes. Useful for checking if your current work introduces issues that were previously flagged.

No parameters required.

**Example**: "Do any of my changes touch files with known findings?"

### `record_decision`

Record a decision about a finding, identical to `noxaudit decide`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `finding_id` | string | The finding ID to decide on |
| `action` | string | `accept`, `dismiss`, or `intentional` |
| `reason` | string | Why this decision was made |

**Example**: "Dismiss finding abc123 because it's a test fixture"

### `run_audit`

Run an on-demand audit from within your coding tool.

| Parameter | Type | Description |
|-----------|------|-------------|
| `focus` | string | Focus area(s) to audit |

**Example**: "Run a security audit on this project"

## Use Cases

- **During development**: Ask your AI assistant "are there any security findings in the file I'm editing?"
- **Code review**: "Show me the health summary for this repo"
- **Triage**: "Dismiss all low-severity hygiene findings"
- **On-demand audits**: "Run a quick security audit" without leaving your editor
