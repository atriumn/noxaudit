"""Pricing data and cost estimation for noxaudit estimate command."""

from __future__ import annotations

from dataclasses import dataclass

from noxaudit.config import normalize_focus


@dataclass
class ModelPricing:
    """Per-model pricing data."""

    input_per_million: float  # $/M tokens, standard tier
    output_per_million: float  # $/M tokens, standard tier
    tier_threshold: int | None  # Input token count above which tiered rates apply
    input_per_million_high: float | None  # $/M tokens, high tier
    output_per_million_high: float | None  # $/M tokens, high tier output
    batch_discount: float = 0.0  # Fraction discount (0.5 = 50%)
    context_window: int = 200_000


MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-opus-4-6": ModelPricing(
        input_per_million=5.00,
        output_per_million=25.00,
        tier_threshold=200_000,
        input_per_million_high=10.00,
        output_per_million_high=37.50,
        batch_discount=0.50,
        context_window=200_000,
    ),
    "claude-sonnet-4-5": ModelPricing(
        input_per_million=3.00,
        output_per_million=15.00,
        tier_threshold=200_000,
        input_per_million_high=6.00,
        output_per_million_high=22.50,
        batch_discount=0.50,
        context_window=200_000,
    ),
    "gemini-2.5-flash": ModelPricing(
        input_per_million=0.30,
        output_per_million=2.50,
        tier_threshold=None,
        input_per_million_high=None,
        output_per_million_high=None,
        batch_discount=0.0,
        context_window=1_000_000,
    ),
    "gemini-2.0-flash": ModelPricing(
        input_per_million=0.10,
        output_per_million=0.40,
        tier_threshold=None,
        input_per_million_high=None,
        output_per_million_high=None,
        batch_discount=0.0,
        context_window=1_000_000,
    ),
}

# Maps each focus area to its "frame" question
FOCUS_FRAMES: dict[str, str] = {
    "security": "Does it work?",
    "testing": "Does it work?",
    "patterns": "Does it last?",
    "hygiene": "Does it last?",
    "docs": "Does it last?",
    "dependencies": "Does it last?",
    "performance": "Does it scale?",
}

# Provider name for each model key
_MODEL_PROVIDER: dict[str, str] = {
    "claude-opus-4-6": "anthropic",
    "claude-sonnet-4-5": "anthropic",
    "gemini-2.5-flash": "gemini",
    "gemini-2.0-flash": "gemini",
}


def resolve_model_key(provider: str, model: str) -> str:
    """Map a provider + model name to a MODEL_PRICING key.

    Tries direct lookup first, then falls back to provider-based heuristics.
    """
    if model in MODEL_PRICING:
        return model
    model_lower = model.lower()
    if provider == "anthropic":
        if "opus" in model_lower:
            return "claude-opus-4-6"
        return "claude-sonnet-4-5"
    elif provider == "gemini":
        if "2.5" in model or "2-5" in model:
            return "gemini-2.5-flash"
        return "gemini-2.0-flash"
    return "gemini-2.0-flash"


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    pricing: ModelPricing,
    use_batch: bool = True,
) -> float:
    """Calculate total cost for given token counts.

    Handles tiered pricing split at threshold. When input exceeds the tier
    threshold, output tokens are also billed at the high tier rate (matching
    Anthropic actual pricing). Batch discount applied last.
    """
    if input_tokens == 0 and output_tokens == 0:
        return 0.0

    if pricing.tier_threshold and input_tokens > pricing.tier_threshold:
        standard_input = pricing.tier_threshold
        high_input = input_tokens - pricing.tier_threshold
        input_cost = (standard_input / 1_000_000) * pricing.input_per_million
        input_cost += (high_input / 1_000_000) * (pricing.input_per_million_high or 0.0)
        output_cost = (output_tokens / 1_000_000) * (pricing.output_per_million_high or 0.0)
    else:
        input_cost = (input_tokens / 1_000_000) * pricing.input_per_million
        output_cost = (output_tokens / 1_000_000) * pricing.output_per_million

    total = input_cost + output_cost

    if use_batch and pricing.batch_discount > 0:
        total *= 1.0 - pricing.batch_discount

    return total


def estimate_output_tokens(input_tokens: int, num_focus_areas: int = 1) -> int:
    """Estimate output tokens: min(16384, input * 0.1) per focus area."""
    per_focus = min(16384, int(input_tokens * 0.1))
    return per_focus * max(1, num_focus_areas)


def estimate_prepass_reduction(files: list, total_tokens: int) -> dict:
    """Estimate what a pre-pass triage would reduce tokens to without running it.

    Sorts files by content size ascending, applies 15% high / 30% medium /
    30% low / 25% skip distribution. Kept files (high + medium) contribute
    to the reduced token count. Triage cost uses gemini-2.5-flash at ~60
    output tokens per file.
    """
    if not files:
        return {"reduced_tokens": 0, "triage_cost": 0.0, "high": 0, "medium": 0, "low_skip": 0}

    n = len(files)
    sorted_files = sorted(files, key=lambda f: len(f.content))

    high_count = max(1, round(n * 0.15))
    medium_count = max(1, round(n * 0.30))
    low_skip_count = n - high_count - medium_count

    # Kept files: high + medium priority (smallest files in ascending sort)
    kept_files = sorted_files[: high_count + medium_count]
    reduced_tokens = sum(len(f.content) // 4 for f in kept_files)

    # Triage cost: run gemini-2.5-flash on all files (~60 output tokens per file)
    flash_pricing = MODEL_PRICING["gemini-2.5-flash"]
    triage_output = n * 60
    triage_cost = estimate_cost(total_tokens, triage_output, flash_pricing, use_batch=False)

    return {
        "reduced_tokens": reduced_tokens,
        "triage_cost": triage_cost,
        "high": high_count,
        "medium": medium_count,
        "low_skip": low_skip_count,
    }


def get_frame_label(focus_names: list[str]) -> str | None:
    """Return shared frame label if all focus areas belong to the same frame."""
    if not focus_names:
        return None
    frames = {FOCUS_FRAMES.get(name) for name in focus_names if name in FOCUS_FRAMES}
    frames.discard(None)  # type: ignore[arg-type]
    if len(frames) == 1:
        return next(iter(frames))
    return None


def count_weekly_runs(schedule: dict) -> int:
    """Count active (non-off) days per week in a schedule dict."""
    return sum(1 for v in schedule.values() if normalize_focus(v))


def _fmt_tokens(n: int) -> str:
    """Format a token count as a human-readable string (287000 → '287K')."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


def build_estimate_report(
    repo_name: str,
    focus_names: list[str],
    files: list,
    provider_name: str,
    model_key: str,
    schedule: dict,
) -> str:
    """Assemble a human-readable cost estimate report."""
    lines: list[str] = [""]

    # Header
    focus_display = " + ".join(focus_names)
    frame = get_frame_label(focus_names)
    header = f"  {repo_name} — {focus_display}"
    if frame:
        header += f" ({frame})"
    lines.append(header)
    lines.append("")

    # Token count (rough: 1 token per 4 chars)
    total_tokens = sum(len(f.content) // 4 for f in files)
    lines.append(f"  Files:     {len(files)} files, {_fmt_tokens(total_tokens)} tokens")

    pricing = MODEL_PRICING[model_key]
    use_batch = pricing.batch_discount > 0
    lines.append(f"  Provider:  {provider_name} ({model_key})")
    lines.append("")

    output_tokens = estimate_output_tokens(total_tokens, len(focus_names))
    cost = estimate_cost(total_tokens, output_tokens, pricing, use_batch=use_batch)
    tiered = bool(pricing.tier_threshold and total_tokens > pricing.tier_threshold)

    if tiered:
        lines.append(f"  ! Cost estimate: ~${cost:.2f}")
        lines.append(
            f"    Your token count ({_fmt_tokens(total_tokens)}) exceeds "
            f"Anthropic's 200K standard tier."
        )
        lines.append(
            f"    Tiered pricing applies: ${pricing.input_per_million_high:.2f}/M input "
            f"(2x standard rate)."
        )
        if use_batch:
            lines.append("    Batch API 50% discount applied.")
    else:
        lines.append(f"  Cost estimate: ~${cost:.2f}")
        if use_batch:
            lines.append("    Batch API 50% discount applied.")
    lines.append("")

    # Alternatives (cheaper models)
    alternatives: list[tuple[str, str, float, int]] = []
    for alt_key, alt_pricing in MODEL_PRICING.items():
        if alt_key == model_key:
            continue
        alt_provider = _MODEL_PROVIDER[alt_key]
        alt_output = estimate_output_tokens(total_tokens, len(focus_names))
        alt_use_batch = alt_pricing.batch_discount > 0
        alt_cost = estimate_cost(total_tokens, alt_output, alt_pricing, use_batch=alt_use_batch)
        if cost > 0 and alt_cost < cost:
            savings_pct = int((1.0 - alt_cost / cost) * 100)
            alternatives.append((alt_key, alt_provider, alt_cost, savings_pct))

    alternatives.sort(key=lambda x: x[2])

    # Pre-pass alternative (only when Anthropic exceeds tier threshold)
    prepass_info: tuple | None = None
    if tiered and provider_name == "anthropic":
        prepass = estimate_prepass_reduction(files, total_tokens)
        reduced_tokens = prepass["reduced_tokens"]
        reduced_output = estimate_output_tokens(reduced_tokens, len(focus_names))
        no_tier_cost = estimate_cost(reduced_tokens, reduced_output, pricing, use_batch=use_batch)
        total_prepass_cost = no_tier_cost + prepass["triage_cost"]
        if cost > 0 and total_prepass_cost < cost:
            pp_savings_pct = int((1.0 - total_prepass_cost / cost) * 100)
            prepass_info = (prepass, reduced_tokens, total_prepass_cost, pp_savings_pct)

    if alternatives or prepass_info:
        lines.append("  Alternatives:")
        for alt_key, alt_provider, alt_cost, savings_pct in alternatives:
            desc = f"{alt_provider} ({alt_key})"
            note = ""
            if alt_provider == "gemini" and savings_pct >= 90:
                note = " — recommended for daily audits"
            elif "sonnet" in alt_key:
                note = " — similar quality, lower cost"
            lines.append(f"    {desc:<38} ~${alt_cost:.2f}   {savings_pct}% cheaper{note}")
        if prepass_info:
            _, _, total_prepass_cost, pp_savings_pct = prepass_info
            desc = f"{provider_name} + pre-pass"
            note = f" — Flash triage keeps {model_key} under 200K tier"
            lines.append(
                f"    {desc:<38} ~${total_prepass_cost:.2f}   {pp_savings_pct}% cheaper{note}"
            )
        lines.append("")

    # Pre-pass detail section
    if prepass_info:
        prepass, reduced_tokens, total_prepass_cost, _ = prepass_info
        lines.append("  Pre-pass estimate:")
        lines.append(f"    Gemini Flash triage: ~${prepass['triage_cost']:.2f}")
        lines.append(
            f"    Expected reduction: {_fmt_tokens(total_tokens)} → "
            f"~{_fmt_tokens(reduced_tokens)} tokens "
            f"(high: {prepass['high']} files, medium: {prepass['medium']}, "
            f"low/skip: {prepass['low_skip']})"
        )
        lines.append(
            f"    With pre-pass, {model_key} stays in standard pricing tier "
            f"(${pricing.input_per_million:.2f}/M vs "
            f"${pricing.input_per_million_high:.2f}/M)"
        )
        lines.append("")

    # Monthly projection
    active_days = count_weekly_runs(schedule)
    monthly_runs = active_days * 52 / 12
    monthly_cost = cost * monthly_runs
    lines.append(
        f"  Monthly estimate: ~${monthly_cost:.2f} ({active_days} runs/week at current schedule)"
    )

    if alternatives:
        cheapest_key, cheapest_provider, cheapest_cost, _ = alternatives[0]
        monthly_cheapest = cheapest_cost * monthly_runs
        lines.append(f"  Monthly with {cheapest_key}: ~${monthly_cheapest:.2f}")

    lines.append("")

    # Recommendation for expensive Anthropic with cheap gemini alternative
    if tiered and alternatives:
        cheapest_key, cheapest_provider, cheapest_cost, _ = alternatives[0]
        if cheapest_provider == "gemini":
            lines.append(
                f"  Recommendation: Use gemini for daily audits (~${cheapest_cost:.2f}/run)."
            )
            lines.append(
                "  Reserve anthropic for monthly deep dives where finding depth matters most."
            )
            lines.append("")

    return "\n".join(lines)
