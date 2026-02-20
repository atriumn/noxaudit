"""Cost ledger for tracking per-audit token usage and costs."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from noxaudit.pricing import MODEL_PRICING, estimate_cost, resolve_model_key


class CostLedger:
    """Manages reading and writing cost ledger entries."""

    LEDGER_PATH = Path(".noxaudit/cost-ledger.jsonl")

    @classmethod
    def append_entry(
        cls,
        repo: str,
        focus: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_write_tokens: int,
        file_count: int,
        timestamp: str | None = None,
    ) -> None:
        """Append an entry to the cost ledger.

        Creates the ledger file if it doesn't exist.
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # Calculate cost using pricing data
        model_key = resolve_model_key(provider, model)
        pricing = MODEL_PRICING.get(model_key)
        if not pricing:
            cost_estimate = 0.0
        else:
            # Use batch API discount if provider is Anthropic
            use_batch = provider.lower() == "anthropic"
            cost_estimate = estimate_cost(
                input_tokens,
                output_tokens,
                pricing,
                use_batch=use_batch,
                cache_read_tokens=cache_read_tokens,
                cache_write_tokens=cache_write_tokens,
            )

        entry = {
            "timestamp": timestamp,
            "repo": repo,
            "focus": focus,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
            "file_count": file_count,
            "cost_estimate_usd": round(cost_estimate, 4),
        }

        cls.LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.LEDGER_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")

    @classmethod
    def read_entries(cls) -> list[dict]:
        """Read all entries from the cost ledger.

        Returns empty list if ledger doesn't exist.
        Gracefully skips malformed lines.
        """
        if not cls.LEDGER_PATH.exists():
            return []

        entries = []
        with open(cls.LEDGER_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

        return entries

    @classmethod
    def get_last_n(cls, n: int) -> list[dict]:
        """Get the last n entries from the ledger."""
        entries = cls.read_entries()
        return entries[-n:] if n > 0 else []

    @classmethod
    def get_last_n_days(cls, days: int) -> list[dict]:
        """Get entries from the last n days."""
        entries = cls.read_entries()
        cutoff = datetime.now() - timedelta(days=days)

        result = []
        for entry in entries:
            try:
                entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                if entry_time >= cutoff:
                    result.append(entry)
            except (ValueError, TypeError):
                # Skip entries with invalid timestamps
                continue

        return result
