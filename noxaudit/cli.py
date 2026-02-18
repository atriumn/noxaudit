"""CLI entrypoint for noxaudit."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import click

from noxaudit import __version__
from noxaudit.config import WEEKDAY_NAMES, load_config, normalize_focus
from noxaudit.decisions import load_decisions, save_decision
from noxaudit.focus import FOCUS_AREAS
from noxaudit.models import Decision, DecisionType
from noxaudit.runner import retrieve_audit, run_audit, submit_audit


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
@click.pass_context
def run(ctx, repo, focus, provider, dry_run):
    """Run an audit."""
    config = load_config(ctx.obj["config_path"])
    results = run_audit(
        config, repo_name=repo, focus_name=focus, provider_name=provider, dry_run=dry_run
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
@click.pass_context
def retrieve(ctx, pending_file):
    """Retrieve results from a previously submitted batch."""
    config = load_config(ctx.obj["config_path"])
    results = retrieve_audit(config, pending_path=pending_file)

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
        names = normalize_focus(raw)
        display = ", ".join(names) if names else "off"
        marker = " ← today" if day == today_name else ""
        icon = "  " if not names else "▶ "
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
    today_raw = config.get_today_focus()
    today_names = normalize_focus(today_raw)
    today_display = ", ".join(today_names) if today_names else "off"
    click.echo(f"Today's focus: {today_display}")


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


if __name__ == "__main__":
    main()
