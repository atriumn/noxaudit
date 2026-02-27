# Installation

## Requirements

- Python 3.11 or higher
- An API key for at least one AI provider

## Install with pip

```bash
pip install noxaudit
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install noxaudit
```

## Optional Extras

Noxaudit supports multiple AI providers. Install the extras for the providers you want to use:

=== "Anthropic (default)"

    Anthropic is included in the base install — no extra needed.

    ```bash
    pip install noxaudit
    ```

=== "OpenAI"

    ```bash
    pip install 'noxaudit[openai]'
    ```

=== "Google Gemini"

    ```bash
    pip install 'noxaudit[google]'
    ```

=== "MCP Server"

    ```bash
    pip install 'noxaudit[mcp]'
    ```

=== "All providers"

    ```bash
    pip install 'noxaudit[openai,google,mcp]'
    ```

## API Key Setup

Set the API key for your chosen provider as an environment variable:

```bash
# Anthropic (default)
export ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
export OPENAI_API_KEY=sk-...

# Google Gemini
export GOOGLE_API_KEY=...
```

!!! tip
    Add your API key to a `.env` file in your project root and load it with `export $(grep -v '^#' .env | xargs)`. Make sure `.env` is in your `.gitignore`.

## Verify Installation

```bash
noxaudit --version
noxaudit --help
```

## Next Steps

- [Quick Start](quickstart.md) — run your first audit in under a minute
- [Configuration](../guides/configuration.md) — set up `noxaudit.yml` for your project
