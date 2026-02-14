"""Main audit runner / orchestrator."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from nightwatch.config import NightwatchConfig
from nightwatch.decisions import filter_findings, format_decision_context, load_decisions
from nightwatch.focus import FOCUS_AREAS
from nightwatch.issues import create_issues_for_findings
from nightwatch.models import AuditResult
from nightwatch.notifications.telegram import send_telegram
from nightwatch.providers.anthropic import AnthropicProvider
from nightwatch.reporter import format_notification, generate_report, save_report


PROVIDERS = {
    "anthropic": AnthropicProvider,
}

PENDING_BATCH_FILE = ".nightwatch/pending-batch.json"
LAST_RETRIEVED_FILE = ".nightwatch/last-retrieved.json"


def submit_audit(
    config: NightwatchConfig,
    repo_name: str | None = None,
    focus_name: str | None = None,
    provider_name: str | None = None,
    dry_run: bool = False,
) -> dict | None:
    """Submit batch audit(s). Returns pending batch info to be retrieved later."""
    focus_name = focus_name or config.get_today_focus()
    if focus_name == "off":
        print("Today is scheduled as off. Use --focus to override.")
        return None

    if focus_name not in FOCUS_AREAS:
        available = ", ".join(FOCUS_AREAS.keys())
        raise ValueError(f"Unknown focus area: {focus_name}. Available: {available}")

    repos = config.repos
    if repo_name:
        repos = [r for r in repos if r.name == repo_name]
        if not repos:
            raise ValueError(f"Unknown repo: {repo_name}")

    pending = {
        "submitted_at": datetime.now().isoformat(),
        "focus": focus_name,
        "batches": [],
    }

    for repo in repos:
        batch_info = _submit_repo(config, repo, focus_name, provider_name, dry_run)
        if batch_info:
            pending["batches"].append(batch_info)

    # Save pending batch info for retrieval later
    if pending["batches"] and not dry_run:
        pending_path = Path(PENDING_BATCH_FILE)
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(json.dumps(pending, indent=2))
        print(f"\nBatch info saved to {PENDING_BATCH_FILE}")
        print("Run `nightwatch retrieve` later to get results.")

    return pending


def retrieve_audit(
    config: NightwatchConfig,
    pending_path: str | None = None,
) -> list[AuditResult]:
    """Retrieve results from a previously submitted batch."""
    path = Path(pending_path or PENDING_BATCH_FILE)
    if not path.exists():
        print(f"No pending batch found at {path}")
        print("Run `nightwatch submit` first.")
        return []

    pending = json.loads(path.read_text())

    if _already_retrieved(pending):
        print("Batch already retrieved — skipping.")
        return []

    focus_name = pending["focus"]
    results = []

    for batch_info in pending["batches"]:
        result = _retrieve_repo(config, batch_info, focus_name)
        if result:
            results.append(result)

    if results:
        _mark_retrieved(pending)
        # Clean up pending file
        path.unlink(missing_ok=True)

    return results


def run_audit(
    config: NightwatchConfig,
    repo_name: str | None = None,
    focus_name: str | None = None,
    provider_name: str | None = None,
    dry_run: bool = False,
) -> list[AuditResult]:
    """Submit and wait for results (convenience for local CLI use)."""
    focus_name = focus_name or config.get_today_focus()
    if focus_name == "off":
        print("Today is scheduled as off. Use --focus to override.")
        return []

    if focus_name not in FOCUS_AREAS:
        available = ", ".join(FOCUS_AREAS.keys())
        raise ValueError(f"Unknown focus area: {focus_name}. Available: {available}")

    repos = config.repos
    if repo_name:
        repos = [r for r in repos if r.name == repo_name]
        if not repos:
            raise ValueError(f"Unknown repo: {repo_name}")

    results = []
    for repo in repos:
        result = _run_repo_sync(config, repo, focus_name, provider_name, dry_run)
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
    path.write_text(json.dumps({
        "batch_ids": batch_ids,
        "retrieved_at": datetime.now().isoformat(),
    }, indent=2))


def _submit_repo(config, repo, focus_name, provider_name, dry_run):
    """Submit a batch for one repo. Returns batch info dict."""
    focus = FOCUS_AREAS[focus_name]()
    print(f"[{repo.name}] Gathering files for {focus_name} audit...")
    files = focus.gather_files(repo.path, repo.exclude_patterns)
    print(f"[{repo.name}] Found {len(files)} files")

    if not files:
        print(f"[{repo.name}] No files to audit, skipping")
        return None

    decisions = load_decisions(config.decisions.path)
    decision_context = format_decision_context(decisions)
    prompt = focus.get_prompt()

    if dry_run:
        print(f"[{repo.name}] DRY RUN — would send {len(files)} files to provider")
        print(f"[{repo.name}] Prompt length: {len(prompt)} chars")
        print(f"[{repo.name}] Decision context: {len(decisions)} prior decisions")
        return None

    pname = provider_name or config.get_provider_for_repo(repo.name)
    if pname not in PROVIDERS:
        raise ValueError(f"Unknown provider: {pname}")

    provider = PROVIDERS[pname](model=config.model)
    custom_id = f"{repo.name}-{focus_name}"
    print(f"[{repo.name}] Submitting {focus_name} batch via {pname} ({config.model})...")

    batch_id = provider.submit_batch(files, prompt, decision_context, custom_id)
    print(f"[{repo.name}] Batch submitted: {batch_id}")

    return {
        "repo": repo.name,
        "batch_id": batch_id,
        "provider": pname,
    }


def _retrieve_repo(config, batch_info, focus_name):
    """Retrieve batch results for one repo."""
    repo_name = batch_info["repo"]
    batch_id = batch_info["batch_id"]
    pname = batch_info["provider"]

    provider = PROVIDERS[pname](model=config.model)
    print(f"[{repo_name}] Checking batch {batch_id}...")

    result = provider.retrieve_batch(batch_id)

    if result["status"] != "ended":
        processing = result["request_counts"]["processing"]
        print(f"[{repo_name}] Still processing ({processing} remaining)")
        return None

    findings = result.get("findings", [])
    print(f"[{repo_name}] Got {len(findings)} findings")

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
        focus=focus_name,
        provider=pname,
        findings=findings,
        new_findings=new_findings,
        resolved_count=resolved_count,
        timestamp=datetime.now().isoformat(),
    )

    # Generate and save report
    report = generate_report(audit_result)
    report_path = save_report(report, config.reports_dir, repo_name, focus_name)
    print(f"[{repo_name}] Report saved to {report_path}")

    # Send notifications
    for notif in config.notifications:
        if notif.channel == "telegram":
            msg = format_notification(audit_result)
            send_telegram(msg, chat_id=notif.target)
            print(f"[{repo_name}] Telegram notification sent")

    # Create GitHub issues
    create_issues_for_findings(audit_result, config.issues)

    return audit_result


def _run_repo_sync(config, repo, focus_name, provider_name, dry_run):
    """Run audit synchronously — submits batch, polls until done."""
    focus = FOCUS_AREAS[focus_name]()
    print(f"[{repo.name}] Gathering files for {focus_name} audit...")
    files = focus.gather_files(repo.path, repo.exclude_patterns)
    print(f"[{repo.name}] Found {len(files)} files")

    if not files:
        return AuditResult(
            repo=repo.name, focus=focus_name, provider="none",
            timestamp=datetime.now().isoformat(),
        )

    decisions = load_decisions(config.decisions.path)
    decision_context = format_decision_context(decisions)
    prompt = focus.get_prompt()

    if dry_run:
        print(f"[{repo.name}] DRY RUN — would send {len(files)} files to provider")
        return AuditResult(
            repo=repo.name, focus=focus_name, provider="dry-run",
            timestamp=datetime.now().isoformat(),
        )

    pname = provider_name or config.get_provider_for_repo(repo.name)
    provider = PROVIDERS[pname](model=config.model)
    print(f"[{repo.name}] Running {focus_name} audit via {pname} (batch API, polling)...")

    findings = provider.run_audit(files, prompt, decision_context)
    print(f"[{repo.name}] Got {len(findings)} findings")

    new_findings, resolved_count = filter_findings(
        findings, decisions, repo.path, config.decisions.expiry_days
    )

    result = AuditResult(
        repo=repo.name, focus=focus_name, provider=pname,
        findings=findings, new_findings=new_findings,
        resolved_count=resolved_count, timestamp=datetime.now().isoformat(),
    )

    report = generate_report(result)
    report_path = save_report(report, config.reports_dir, repo.name, focus_name)
    print(f"[{repo.name}] Report saved to {report_path}")

    for notif in config.notifications:
        if notif.channel == "telegram":
            msg = format_notification(result)
            send_telegram(msg, chat_id=notif.target)

    # Create GitHub issues
    create_issues_for_findings(result, config.issues)

    return result
