"""CLI entrypoint for noxaudit."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import click

from noxaudit import __version__
from noxaudit.config import WEEKDAY_NAMES, load_config, normalize_focus
from noxaudit.cost_ledger import CostLedger
from noxaudit.frames import FRAME_LABELS, FRAMES, get_enabled_focus_areas
from noxaudit.decisions import (
    create_baseline_decisions,
    list_baseline_decisions,
    load_decisions,
    remove_baseline_decisions,
    save_decision,
)
from noxaudit.focus import FOCUS_AREAS
from noxaudit.models import Decision, DecisionType
from noxaudit.runner import retrieve_audit, run_audit, submit_audit


def _format_tokens(n: int) -> str:
    """Format token count as human-readable (287000 -> '287K')."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


def _display_cost_summary() -> None:
    """Display cost tracking summary from ledger."""
    entries = CostLedger.get_last_n_days(30)

    if not entries:
        click.echo("")
        click.echo("Cost (last 30 days):")
        click.echo("  No audit history yet")
        return

    # Calculate aggregates
    total_input = sum(e.get("input_tokens", 0) for e in entries)
    total_output = sum(e.get("output_tokens", 0) for e in entries)
    total_cache_read = sum(e.get("cache_read_tokens", 0) for e in entries)
    total_cache_write = sum(e.get("cache_write_tokens", 0) for e in entries)
    total_cost = sum(e.get("cost_estimate_usd", 0) for e in entries)
    avg_cost = total_cost / len(entries) if entries else 0

    # Project monthly using actual days with data (not a hardcoded 30/30 = 1x)
    from datetime import datetime as _dt

    timestamps = []
    for e in entries:
        try:
            timestamps.append(_dt.fromisoformat(e.get("timestamp", "")))
        except (ValueError, TypeError):
            pass
    if len(timestamps) > 1:
        days_with_data = max((max(timestamps).date() - min(timestamps).date()).days, 1)
    else:
        days_with_data = 1
    projected_monthly = (total_cost / days_with_data) * 30

    click.echo("")
    click.echo("Cost (last 30 days):")
    click.echo(f"  Audits run:          {len(entries)}")
    click.echo(f"  Total input tokens:  {_format_tokens(total_input)}")
    click.echo(f"  Total output tokens: {_format_tokens(total_output)}")
    if total_cache_read or total_cache_write:
        click.echo(f"  Cache read tokens:   {_format_tokens(total_cache_read)}")
        click.echo(f"  Cache write tokens:  {_format_tokens(total_cache_write)}")
        total_input_processed = total_input + total_cache_read
        if total_input_processed > 0:
            cache_pct = total_cache_read / total_input_processed * 100
            click.echo(f"  Cache savings:       {cache_pct:.1f}% served from cache")
    click.echo(f"  Estimated spend:     ${total_cost:.2f}")
    click.echo(f"  Avg per audit:       ${avg_cost:.2f}")
    click.echo(f"  Projected monthly:   ~${projected_monthly:.2f}")

    # Show last 5 audits
    last_5 = entries[-5:] if len(entries) >= 5 else entries
    if last_5:
        click.echo("")
        click.echo("  Last 5 audits:")
        for entry in reversed(last_5):
            timestamp = entry.get("timestamp", "")
            # Parse ISO timestamp and format as date
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(timestamp)
                date_str = dt.strftime("%b %d")
            except (ValueError, TypeError):
                date_str = "unknown"

            focus = entry.get("focus", "")
            model = entry.get("model", "")
            file_count = entry.get("file_count", 0)
            total_tokens = entry.get("input_tokens", 0) + entry.get("output_tokens", 0)
            cost = entry.get("cost_estimate_usd", 0)

            click.echo(
                f"    {date_str}  {focus:<18} {model:<20} {file_count:>3} files  "
                f"{_format_tokens(total_tokens):>7} tok  ${cost:.2f}"
            )


@click.group()
@click.version_option(version=__version__)
@click.option("--config", "-c", "config_path", default=None, help="Path to noxaudit.yml")
@click.pass_context
def main(ctx, config_path):
    """Noxaudit: Nightly AI-powered codebase audits."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


@main.command()
@click.option("--repo", "-r", default=None, help="Audit a specific repo (default: all)")
@click.option("--focus", "-f", default=None, help="Focus area(s): name, comma-separated, or 'all'")
@click.option("--provider", "-p", default=None, help="AI provider (default: from config)")
@click.option("--dry-run", is_flag=True, help="Show what would be audited without calling AI")
@click.option(
    "--format",
    "-F",
    "output_format",
    type=click.Choice(["markdown", "sarif"]),
    default="markdown",
    help="Output format: markdown (default) or sarif (for GitHub Code Scanning)",
)
@click.pass_context
def run(ctx, repo, focus, provider, dry_run, output_format):
    """Run an audit."""
    config = load_config(ctx.obj["config_path"])
    results = run_audit(
        config,
        repo_name=repo,
        focus_name=focus,
        provider_name=provider,
        dry_run=dry_run,
        output_format=output_format,
    )

    for result in results:
        if result.new_findings:
            click.echo(f"\n{result.repo}: {len(result.new_findings)} new findings")
        else:
            click.echo(f"\n{result.repo}: No new findings ✓")


@main.command()
@click.option("--repo", "-r", default=None, help="Audit a specific repo (default: all)")
@click.option("--focus", "-f", default=None, help="Focus area(s): name, comma-separated, or 'all'")
@click.option("--provider", "-p", default=None, help="AI provider (default: from config)")
@click.option("--dry-run", is_flag=True, help="Show what would be audited without calling AI")
@click.pass_context
def submit(ctx, repo, focus, provider, dry_run):
    """Submit a batch audit (returns immediately, results retrieved later)."""
    config = load_config(ctx.obj["config_path"])
    pending = submit_audit(
        config, repo_name=repo, focus_name=focus, provider_name=provider, dry_run=dry_run
    )

    if pending and pending["batches"]:
        click.echo(
            f"\nSubmitted {len(pending['batches'])} batch(es). Run `noxaudit retrieve` to get results."
        )
    elif not dry_run:
        click.echo("Nothing to submit.")


@main.command()
@click.option("--pending-file", default=None, help="Path to pending batch JSON file")
@click.option(
    "--format",
    "-F",
    "output_format",
    type=click.Choice(["markdown", "sarif"]),
    default="markdown",
    help="Output format: markdown (default) or sarif (for GitHub Code Scanning)",
)
@click.pass_context
def retrieve(ctx, pending_file, output_format):
    """Retrieve results from a previously submitted batch."""
    config = load_config(ctx.obj["config_path"])
    results = retrieve_audit(config, pending_path=pending_file, output_format=output_format)

    if not results:
        click.echo("No results ready yet. Batch may still be processing.")
        return

    for result in results:
        if result.new_findings:
            click.echo(f"\n{result.repo}: {len(result.new_findings)} new findings")
        else:
            click.echo(f"\n{result.repo}: No new findings ✓")


@main.command()
@click.argument("finding_id")
@click.option(
    "--action",
    "-a",
    type=click.Choice(["accept", "dismiss", "intentional"]),
    required=True,
    help="Decision type",
)
@click.option("--reason", "-r", required=True, help="Why this decision was made")
@click.option("--by", "-b", default="user", help="Who made this decision")
@click.pass_context
def decide(ctx, finding_id, action, reason, by):
    """Record a decision about a finding."""
    config = load_config(ctx.obj["config_path"])

    type_map = {
        "accept": DecisionType.ACCEPTED,
        "dismiss": DecisionType.DISMISSED,
        "intentional": DecisionType.INTENTIONAL,
    }
    decision = Decision(
        finding_id=finding_id,
        decision=type_map[action],
        reason=reason,
        date=date.today().isoformat(),
        by=by,
    )

    save_decision(config.decisions.path, decision)
    click.echo(f"Decision recorded: {action} finding {finding_id}")


@main.command()
@click.pass_context
def schedule(ctx):
    """Show the weekly audit schedule."""
    config = load_config(ctx.obj["config_path"])

    click.echo("Weekly Schedule:")
    click.echo("")
    today_name = WEEKDAY_NAMES[date.today().weekday()]
    for day in WEEKDAY_NAMES:
        raw = config.schedule.get(day, "off")
        raw_str = str(raw) if not isinstance(raw, list) else None

        if raw_str and raw_str in FRAMES:
            # Frame-based entry: show label + active focus areas
            fc = config.frames.get(raw_str)
            overrides = fc.overrides if fc else None
            focuses = get_enabled_focus_areas(raw_str, overrides)
            label = FRAME_LABELS[raw_str]
            display = f"{label} ({', '.join(focuses)})" if focuses else f"{label} (none active)"
            active = bool(focuses)
        else:
            names = normalize_focus(raw)
            display = ", ".join(names) if names else "off"
            active = bool(names)

        marker = " ← today" if day == today_name else ""
        icon = "▶ " if active else "  "
        click.echo(f"  {icon}{day.capitalize():12s} {display}{marker}")


@main.command()
@click.pass_context
def status(ctx):
    """Show current configuration and status."""
    config = load_config(ctx.obj["config_path"])

    click.echo(f"Noxaudit v{__version__}")
    click.echo("")

    click.echo("Repos:")
    for repo in config.repos:
        providers = ", ".join(repo.provider_rotation)
        click.echo(f"  {repo.name}: {repo.path} ({providers})")

    if not config.repos:
        click.echo("  (none configured)")

    click.echo("")
    click.echo("Focus areas:")
    for name, cls in FOCUS_AREAS.items():
        click.echo(f"  {name}: {cls.description}")

    click.echo("")
    click.echo(f"Model: {config.model}")
    click.echo(f"Decisions: {config.decisions.path}")
    click.echo(f"Reports: {config.reports_dir}")

    decisions = load_decisions(config.decisions.path)
    if decisions:
        click.echo(f"  {len(decisions)} decisions recorded")

    click.echo("")
    import datetime

    today_day = WEEKDAY_NAMES[datetime.date.today().weekday()]
    today_entry = config.schedule.get(today_day, "off")
    today_entry_str = str(today_entry) if not isinstance(today_entry, list) else None

    if today_entry_str and today_entry_str in FRAMES:
        fc = config.frames.get(today_entry_str)
        overrides = fc.overrides if fc else None
        focuses = get_enabled_focus_areas(today_entry_str, overrides)
        label = FRAME_LABELS[today_entry_str]
        today_display = f"{label} ({', '.join(focuses)})" if focuses else f"{label} (none active)"
    else:
        today_raw = config.get_today_focus()
        today_names = normalize_focus(today_raw)
        today_display = ", ".join(today_names) if today_names else "off"

    click.echo(f"Today's focus: {today_display}")

    # Cost tracking section
    _display_cost_summary()


@main.command()
@click.option("--repo", "-r", default=None, help="Show report for a specific repo")
@click.option("--focus", "-f", default=None, help="Show report for a specific focus area")
@click.pass_context
def report(ctx, repo, focus):
    """Show the latest report."""
    config = load_config(ctx.obj["config_path"])
    reports_dir = Path(config.reports_dir)

    if not reports_dir.exists():
        click.echo("No reports yet. Run `noxaudit run` first.")
        return

    # Find latest report
    reports = sorted(reports_dir.rglob("*.md"), reverse=True)

    if repo:
        reports = [r for r in reports if repo in str(r)]
    if focus:
        reports = [r for r in reports if focus in r.name]

    if not reports:
        click.echo("No matching reports found.")
        return

    latest = reports[0]
    click.echo(latest.read_text())


@main.command()
@click.option("--repo", "-r", default=None, help="Estimate for a specific repo (default: all)")
@click.option("--focus", "-f", default=None, help="Focus area(s): name, comma-separated, or 'all'")
@click.option("--provider", "-p", default=None, help="AI provider (default: from config)")
@click.pass_context
def estimate(ctx, repo, focus, provider):
    """Estimate audit cost before running (no API keys needed)."""
    from noxaudit.focus import FOCUS_AREAS
    from noxaudit.focus.base import gather_files_combined
    from noxaudit.pricing import build_estimate_report, resolve_model_key
    from noxaudit.runner import _resolve_focus_names

    config = load_config(ctx.obj["config_path"])

    try:
        focus_names = _resolve_focus_names(focus, config)
    except ValueError as e:
        raise click.ClickException(str(e))

    if not focus_names:
        click.echo("Today is scheduled as off. Use --focus to override.")
        return

    repos = config.repos
    if repo:
        repos = [r for r in repos if r.name == repo]
        if not repos:
            raise click.ClickException(f"Unknown repo: {repo}")

    if not repos:
        click.echo("No repos configured. Add repos to noxaudit.yml.")
        return

    for repo_cfg in repos:
        focus_instances = [FOCUS_AREAS[name]() for name in focus_names]
        files = gather_files_combined(focus_instances, repo_cfg.path, repo_cfg.exclude_patterns)

        if not files:
            click.echo(f"\n  {repo_cfg.name}: No files found matching focus areas.")
            continue

        pname = provider or config.get_provider_for_repo(repo_cfg.name)
        model_key = resolve_model_key(pname, config.model)

        report = build_estimate_report(
            repo_name=repo_cfg.name,
            focus_names=focus_names,
            files=files,
            provider_name=pname,
            model_key=model_key,
            schedule=config.schedule,
        )
        click.echo(report)


@main.command("mcp-server")
def mcp_server():
    """Start the MCP server for AI coding tool integration."""
    try:
        from noxaudit.mcp.server import run_server
    except ImportError:
        click.echo("MCP support requires the 'mcp' package.")
        click.echo("Install with: pip install 'noxaudit[mcp]'")
        raise SystemExit(1)

    run_server()


@main.command()
@click.option("--repo", "-r", default=None, help="Baseline a specific repo")
@click.option("--focus", "-f", default=None, help="Baseline specific focus area(s)")
@click.option(
    "--severity", "-s", default=None, help="Baseline specific severities (low,medium,high)"
)
@click.option("--undo", is_flag=True, help="Remove baseline decisions")
@click.option("--list", "list_baselines", is_flag=True, help="Show baselined findings")
@click.pass_context
def baseline(ctx, repo, focus, severity, undo, list_baselines):
    """Baseline existing findings to suppress them in future audits."""
    config = load_config(ctx.obj["config_path"])

    if list_baselines:
        baselines = list_baseline_decisions(config.decisions.path)
        if not baselines:
            click.echo("No baselined findings.")
            return
        click.echo(f"{len(baselines)} baselined finding(s).")
        click.echo("Run `noxaudit baseline --undo` to remove all baselines.")
        return

    if undo:
        if repo or focus or severity:
            # Filter stored baseline decisions directly — do not rely on the
            # ephemeral latest-findings.json which may be stale or empty.
            all_baselines = list_baseline_decisions(config.decisions.path)
            finding_ids: set[str] = set()
            focus_names = [f.strip() for f in focus.split(",") if f.strip()] if focus else None
            sev_names = (
                [s.strip().lower() for s in severity.split(",") if s.strip()] if severity else None
            )
            for d in all_baselines:
                if repo and d.repo != repo:
                    continue
                if focus_names and d.focus not in focus_names:
                    continue
                if sev_names and d.severity not in sev_names:
                    continue
                finding_ids.add(d.finding_id)
            removed = remove_baseline_decisions(config.decisions.path, finding_ids=finding_ids)
        else:
            removed = remove_baseline_decisions(config.decisions.path)
        label = f" for {repo}" if repo else ""
        click.echo(f"Removed {removed} baseline decisions{label}.")
        return

    # Main baseline: load findings and create decisions
    findings = _load_findings_for_baseline(config, repo, focus, severity)

    if not findings:
        if repo:
            click.echo(
                f"No findings to baseline for {repo}. Run `noxaudit run --repo {repo}` first."
            )
        else:
            click.echo("No findings to baseline. Run `noxaudit run` first.")
        return

    repo_path = "."
    if repo:
        for r in config.repos:
            if r.name == repo:
                repo_path = r.path
                break

    decisions = create_baseline_decisions(findings, repo_path, repo_name=repo)
    for decision in decisions:
        save_decision(config.decisions.path, decision)

    click.echo(f"Baselined {len(decisions)} findings from latest audit.")
    click.echo("These will not appear in future reports unless the affected files change.")
    click.echo("Run `noxaudit baseline --undo` to reverse.")


def _load_findings_for_baseline(config, repo, focus, severity):
    """Load and filter findings from latest-findings.json for baseline operations."""
    from noxaudit.mcp.state import load_latest_findings

    findings = load_latest_findings(".")

    if not findings and repo:
        for r in config.repos:
            if r.name == repo:
                findings = load_latest_findings(r.path)
                break

    if focus:
        focus_names = [f.strip() for f in focus.split(",") if f.strip()]
        findings = [f for f in findings if f.focus in focus_names]

    if severity:
        sev_names = [s.strip().lower() for s in severity.split(",") if s.strip()]
        findings = [f for f in findings if f.severity.value in sev_names]

    return findings


if __name__ == "__main__":
    main()
