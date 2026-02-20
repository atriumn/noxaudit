"""Main audit runner / orchestrator."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from noxaudit.config import NoxauditConfig, normalize_focus
from noxaudit.cost_ledger import CostLedger
from noxaudit.decisions import filter_findings, format_decision_context, load_decisions
from noxaudit.focus import FOCUS_AREAS
from noxaudit.focus.base import build_combined_prompt, gather_files_combined
from noxaudit.issues import create_issues_for_findings
from noxaudit.mcp.state import save_latest_findings
from noxaudit.models import AuditResult, FileContent
from noxaudit.notifications.telegram import send_telegram
from noxaudit.pricing import MODEL_PRICING
from noxaudit.providers.anthropic import AnthropicProvider
from noxaudit.providers.gemini import GeminiProvider
from noxaudit.reporter import format_notification, generate_report, save_report
from noxaudit.sarif import findings_to_sarif, save_sarif


PROVIDERS = {
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}

try:
    from noxaudit.providers.openai import OpenAIProvider

    PROVIDERS["openai"] = OpenAIProvider
except ImportError:
    pass

PENDING_BATCH_FILE = ".noxaudit/pending-batch.json"
LAST_RETRIEVED_FILE = ".noxaudit/last-retrieved.json"


def _resolve_focus_names(
    focus_override: str | None,
    config: NoxauditConfig,
) -> list[str]:
    """Resolve focus names from override or today's schedule. Returns list of names."""
    raw = focus_override or config.get_today_focus()
    names = normalize_focus(raw)
    if not names:
        return []

    available = set(FOCUS_AREAS.keys())
    for name in names:
        if name not in available:
            raise ValueError(
                f"Unknown focus area: {name}. Available: {', '.join(sorted(available))}"
            )
    return names


def _focus_label(names: list[str]) -> str:
    """Create a display label for focus names: 'security+performance'."""
    return "+".join(names)


def estimate_tokens(files: list[FileContent]) -> int:
    """Estimate token count from files. Rough heuristic: ~4 chars per token."""
    total_chars = sum(len(f.content) for f in files)
    return total_chars // 4


def _maybe_prepass(
    files: list[FileContent],
    focus_names: list[str],
    config: NoxauditConfig,
    repo_name: str,
    provider_name: str,
) -> tuple[bool, list[FileContent], str]:
    """Check if pre-pass should be run based on config or provider economics.

    Returns:
        (should_run_prepass, filtered_files, message)
        - should_run_prepass: True if pre-pass should be run
        - filtered_files: Files to use (may be same as input if no prepass)
        - message: Message to print (explaining why prepass was triggered, or empty)
    """
    token_estimate = estimate_tokens(files)

    # Check explicit config: prepass.enabled && tokens > threshold
    if config.prepass.enabled and token_estimate > config.prepass.threshold_tokens:
        return (True, files, "")

    # Check provider economics: Anthropic + tokens > 200K (tier threshold)
    # Only check this if auto_disable is False (auto-enable is enabled)
    if config.prepass.auto_disable:
        return (False, files, "")

    # Determine model key for provider
    model_key = config.model
    pricing = MODEL_PRICING.get(model_key)

    if pricing and pricing.tier_threshold is not None:
        if token_estimate > pricing.tier_threshold:
            # Auto-enable pre-pass with explanatory message
            savings_ratio = 0.5  # Rough estimate: pre-pass reduces tokens by ~50%
            tokens_after_prepass = int(token_estimate * savings_ratio)
            cost_before = (token_estimate / 1_000_000) * pricing.input_per_million
            cost_after = (
                (tokens_after_prepass / 1_000_000) * pricing.input_per_million_high
                if pricing.input_per_million_high
                else cost_before
            )
            savings = cost_before - cost_after

            msg = (
                f"  [{repo_name}] Auto-enabling pre-pass: {token_estimate // 1000}K tokens would hit tiered pricing.\n"
                f"           Pre-pass reduces to ~{tokens_after_prepass // 1000}K tokens, saving ~${savings:.2f} per audit.\n"
                f"           To disable: set prepass.auto: false in config."
            )
            return (True, files, msg)

    return (False, files, "")


def submit_audit(
    config: NoxauditConfig,
    repo_name: str | None = None,
    focus_name: str | None = None,
    provider_name: str | None = None,
    dry_run: bool = False,
) -> dict | None:
    """Submit batch audit(s). Returns pending batch info to be retrieved later."""
    focus_names = _resolve_focus_names(focus_name, config)
    if not focus_names:
        print("Today is scheduled as off. Use --focus to override.")
        return None

    repos = config.repos
    if repo_name:
        repos = [r for r in repos if r.name == repo_name]
        if not repos:
            raise ValueError(f"Unknown repo: {repo_name}")

    label = _focus_label(focus_names)
    pending = {
        "submitted_at": datetime.now().isoformat(),
        "focus": label,
        "focus_names": focus_names,
        "batches": [],
    }

    for repo in repos:
        batch_info = _submit_repo(config, repo, focus_names, provider_name, dry_run)
        if batch_info:
            pending["batches"].append(batch_info)

    # Save pending batch info for retrieval later
    if pending["batches"] and not dry_run:
        pending_path = Path(PENDING_BATCH_FILE)
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(json.dumps(pending, indent=2))
        print(f"\nBatch info saved to {PENDING_BATCH_FILE}")
        print("Run `noxaudit retrieve` later to get results.")

    return pending


def retrieve_audit(
    config: NoxauditConfig,
    pending_path: str | None = None,
    output_format: str = "markdown",
) -> list[AuditResult]:
    """Retrieve results from a previously submitted batch."""
    path = Path(pending_path or PENDING_BATCH_FILE)
    if not path.exists():
        print(f"No pending batch found at {path}")
        print("Run `noxaudit submit` first.")
        return []

    pending = json.loads(path.read_text())

    if _already_retrieved(pending):
        print("Batch already retrieved — skipping.")
        return []

    # Support both old (str) and new (list) format
    focus_names = pending.get("focus_names") or [pending["focus"]]
    label = _focus_label(focus_names)
    default_focus = focus_names[0] if len(focus_names) == 1 else None
    results = []

    for batch_info in pending["batches"]:
        result = _retrieve_repo(config, batch_info, label, default_focus, output_format)
        if result:
            results.append(result)

    if results:
        _mark_retrieved(pending)
        # Clean up pending file
        path.unlink(missing_ok=True)

    return results


def run_audit(
    config: NoxauditConfig,
    repo_name: str | None = None,
    focus_name: str | None = None,
    provider_name: str | None = None,
    dry_run: bool = False,
    output_format: str = "markdown",
) -> list[AuditResult]:
    """Submit and wait for results (convenience for local CLI use)."""
    focus_names = _resolve_focus_names(focus_name, config)
    if not focus_names:
        print("Today is scheduled as off. Use --focus to override.")
        return []

    repos = config.repos
    if repo_name:
        repos = [r for r in repos if r.name == repo_name]
        if not repos:
            raise ValueError(f"Unknown repo: {repo_name}")

    results = []
    for repo in repos:
        result = _run_repo_sync(config, repo, focus_names, provider_name, dry_run, output_format)
        results.append(result)

    return results


def _already_retrieved(pending: dict) -> bool:
    """Check if this batch was already retrieved (idempotency guard)."""
    path = Path(LAST_RETRIEVED_FILE)
    if not path.exists():
        return False
    try:
        last = json.loads(path.read_text())
        pending_ids = sorted(b["batch_id"] for b in pending.get("batches", []))
        retrieved_ids = sorted(last.get("batch_ids", []))
        return pending_ids == retrieved_ids and len(pending_ids) > 0
    except (json.JSONDecodeError, KeyError):
        return False


def _mark_retrieved(pending: dict) -> None:
    """Record batch IDs as retrieved to prevent re-processing."""
    path = Path(LAST_RETRIEVED_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    batch_ids = [b["batch_id"] for b in pending.get("batches", [])]
    path.write_text(
        json.dumps(
            {
                "batch_ids": batch_ids,
                "retrieved_at": datetime.now().isoformat(),
            },
            indent=2,
        )
    )


def _submit_repo(config, repo, focus_names, provider_name, dry_run):
    """Submit a batch for one repo. Returns batch info dict."""
    label = _focus_label(focus_names)
    focus_instances = [FOCUS_AREAS[name]() for name in focus_names]

    print(f"[{repo.name}] Gathering files for {label} audit...")
    files = gather_files_combined(focus_instances, repo.path, repo.exclude_patterns)
    print(f"[{repo.name}] Found {len(files)} files ({len(focus_names)} focus area(s))")

    if not files:
        print(f"[{repo.name}] No files to audit, skipping")
        return None

    # Resolve provider early so _maybe_prepass can check economics
    pname = provider_name or config.get_provider_for_repo(repo.name)
    if pname not in PROVIDERS:
        raise ValueError(f"Unknown provider: {pname}")

    # Check if pre-pass should run (based on config or provider economics)
    should_run_prepass, files, prepass_msg = _maybe_prepass(
        files, focus_names, config, repo.name, pname
    )
    if prepass_msg:
        print(prepass_msg)

    decisions = load_decisions(config.decisions.path)
    decision_context = format_decision_context(decisions)
    prompt = build_combined_prompt(focus_instances)

    if dry_run:
        print(f"[{repo.name}] DRY RUN — would send {len(files)} files to provider")
        print(f"[{repo.name}] Focus areas: {', '.join(focus_names)}")
        print(f"[{repo.name}] Prompt length: {len(prompt)} chars")
        print(f"[{repo.name}] Decision context: {len(decisions)} prior decisions")
        return None

    provider = PROVIDERS[pname](model=config.model)
    custom_id = f"{repo.name}-{label}"
    print(f"[{repo.name}] Submitting {label} batch via {pname} ({config.model})...")

    batch_id = provider.submit_batch(
        files,
        prompt,
        decision_context,
        custom_id,
        num_focus_areas=len(focus_names),
    )
    print(f"[{repo.name}] Batch submitted: {batch_id}")

    return {
        "repo": repo.name,
        "batch_id": batch_id,
        "provider": pname,
        "file_count": len(files),
    }


def _retrieve_repo(config, batch_info, focus_label, default_focus, output_format="markdown"):
    """Retrieve batch results for one repo."""
    repo_name = batch_info["repo"]
    batch_id = batch_info["batch_id"]
    pname = batch_info["provider"]

    provider = PROVIDERS[pname](model=config.model)
    print(f"[{repo_name}] Checking batch {batch_id}...")

    result = provider.retrieve_batch(batch_id, default_focus=default_focus)

    if result["status"] != "ended":
        processing = result["request_counts"]["processing"]
        print(f"[{repo_name}] Still processing ({processing} remaining)")
        return None

    findings = result.get("findings", [])
    print(f"[{repo_name}] Got {len(findings)} findings")

    # Log cost ledger entry
    file_count = batch_info.get("file_count", 0)
    if file_count > 0:
        usage = provider.get_last_usage()
        CostLedger.append_entry(
            repo=repo_name,
            focus=focus_label,
            provider=pname,
            model=config.model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_tokens", 0),
            cache_write_tokens=usage.get("cache_write_tokens", 0),
            file_count=file_count,
        )

    # Find repo config for path
    repo_config = next((r for r in config.repos if r.name == repo_name), None)
    repo_path = repo_config.path if repo_config else "."

    # Filter against decisions
    decisions = load_decisions(config.decisions.path)
    new_findings, resolved_count = filter_findings(
        findings, decisions, repo_path, config.decisions.expiry_days
    )

    audit_result = AuditResult(
        repo=repo_name,
        focus=focus_label,
        provider=pname,
        findings=findings,
        new_findings=new_findings,
        resolved_count=resolved_count,
        timestamp=datetime.now().isoformat(),
    )

    # Serialize findings for MCP tools
    save_latest_findings(
        findings=new_findings,
        repo=repo_name,
        focus=focus_label,
        timestamp=audit_result.timestamp,
        resolved_count=resolved_count,
    )

    # Generate and save report
    report = generate_report(audit_result)
    report_path = save_report(report, config.reports_dir, repo_name, focus_label)
    print(f"[{repo_name}] Report saved to {report_path}")

    if output_format == "sarif":
        sarif = findings_to_sarif(audit_result.findings, focus_label, repo_name)
        sarif_path = save_sarif(sarif, config.reports_dir, repo_name, focus_label)
        print(f"[{repo_name}] SARIF report saved to {sarif_path}")

    # Send notifications
    for notif in config.notifications:
        if notif.channel == "telegram":
            msg = format_notification(audit_result)
            send_telegram(msg, chat_id=notif.target)
            print(f"[{repo_name}] Telegram notification sent")

    # Create GitHub issues
    create_issues_for_findings(audit_result, config.issues)

    return audit_result


def _run_repo_sync(config, repo, focus_names, provider_name, dry_run, output_format="markdown"):
    """Run audit synchronously — submits batch, polls until done."""
    label = _focus_label(focus_names)
    focus_instances = [FOCUS_AREAS[name]() for name in focus_names]

    print(f"[{repo.name}] Gathering files for {label} audit...")
    files = gather_files_combined(focus_instances, repo.path, repo.exclude_patterns)
    print(f"[{repo.name}] Found {len(files)} files ({len(focus_names)} focus area(s))")

    if not files:
        return AuditResult(
            repo=repo.name,
            focus=label,
            provider="none",
            timestamp=datetime.now().isoformat(),
        )

    # Resolve provider early so _maybe_prepass can check economics
    pname = provider_name or config.get_provider_for_repo(repo.name)
    if pname not in PROVIDERS:
        raise ValueError(f"Unknown provider: {pname}")

    # Check if pre-pass should run (based on config or provider economics)
    should_run_prepass, files, prepass_msg = _maybe_prepass(
        files, focus_names, config, repo.name, pname
    )
    if prepass_msg:
        print(prepass_msg)

    decisions = load_decisions(config.decisions.path)
    decision_context = format_decision_context(decisions)
    prompt = build_combined_prompt(focus_instances)

    if dry_run:
        print(f"[{repo.name}] DRY RUN — would send {len(files)} files to provider")
        print(f"[{repo.name}] Focus areas: {', '.join(focus_names)}")
        return AuditResult(
            repo=repo.name,
            focus=label,
            provider="dry-run",
            timestamp=datetime.now().isoformat(),
        )

    provider = PROVIDERS[pname](model=config.model)
    print(f"[{repo.name}] Running {label} audit via {pname} (batch API, polling)...")

    default_focus = focus_names[0] if len(focus_names) == 1 else None
    findings = provider.run_audit(
        files,
        prompt,
        decision_context,
        num_focus_areas=len(focus_names),
        default_focus=default_focus,
    )
    print(f"[{repo.name}] Got {len(findings)} findings")

    # Log cost ledger entry
    usage = provider.get_last_usage()
    CostLedger.append_entry(
        repo=repo.name,
        focus=label,
        provider=pname,
        model=config.model,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_read_tokens=usage.get("cache_read_tokens", 0),
        cache_write_tokens=usage.get("cache_write_tokens", 0),
        file_count=len(files),
    )

    new_findings, resolved_count = filter_findings(
        findings, decisions, repo.path, config.decisions.expiry_days
    )

    result = AuditResult(
        repo=repo.name,
        focus=label,
        provider=pname,
        findings=findings,
        new_findings=new_findings,
        resolved_count=resolved_count,
        timestamp=datetime.now().isoformat(),
    )

    # Serialize findings for MCP tools
    save_latest_findings(
        findings=new_findings,
        repo=repo.name,
        focus=label,
        timestamp=result.timestamp,
        resolved_count=resolved_count,
    )

    report = generate_report(result)
    report_path = save_report(report, config.reports_dir, repo.name, label)
    print(f"[{repo.name}] Report saved to {report_path}")

    if output_format == "sarif":
        sarif = findings_to_sarif(result.findings, label, repo.name)
        sarif_path = save_sarif(sarif, config.reports_dir, repo.name, label)
        print(f"[{repo.name}] SARIF report saved to {sarif_path}")

    for notif in config.notifications:
        if notif.channel == "telegram":
            msg = format_notification(result)
            send_telegram(msg, chat_id=notif.target)

    # Create GitHub issues
    create_issues_for_findings(result, config.issues)

    return result
