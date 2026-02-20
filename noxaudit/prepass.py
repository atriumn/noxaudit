"""Pre-pass file classification to reduce audit costs."""

from __future__ import annotations

from noxaudit.models import ContentTier, FileClassification, FileContent, PrepassResult

# Classification prompt: asks the provider to classify files into content tiers.
# We reuse the existing run_audit() interface — severity encodes the tier:
#   high   → send full file content to the main audit
#   medium → extract and send a representative snippet
#   low    → extract and send only the file's structural map
#   (no finding) → skip — do not include in main audit
CLASSIFICATION_PROMPT = """You are a file relevance classifier for a code audit tool.

Audit focus areas: {focus_names}

Review the provided files and classify each one by how much content the main auditor
will need to assess it for the specified focus areas.

Output a finding for EACH file that should be included in the main audit:
  - severity: "high"   → file is highly relevant; send full content
  - severity: "medium" → file is moderately relevant; a snippet is enough
  - severity: "low"    → file is marginally relevant; a structural map is enough
  - title: one of "full-content", "snippet", or "file-map" (matching the severity above)
  - file: <exact file path as provided — do not change the path>
  - description: one-sentence reason for this classification

For files that are clearly NOT relevant (auto-generated files, lock files, build artifacts,
or configs completely unrelated to {focus_names}), omit them — output no finding.

When in doubt, INCLUDE the file (at least as "low"/file-map). The goal is to filter
only obviously irrelevant files to reduce token costs, not to perform a full audit."""


def build_classification_prompt(focus_names: list[str]) -> str:
    """Build the system prompt for pre-pass classification."""
    focus_str = ", ".join(focus_names)
    return CLASSIFICATION_PROMPT.format(focus_names=focus_str)


def _severity_to_tier(severity_value: str) -> ContentTier:
    """Map a finding severity to a content tier."""
    if severity_value == "high":
        return ContentTier.FULL
    if severity_value == "medium":
        return ContentTier.SNIPPET
    # low or anything else → structural map only
    return ContentTier.MAP


def enrich_files(
    files: list[FileContent],
    classified: list[FileClassification],
) -> list[FileContent]:
    """Build the enriched file list for the main audit.

    - FULL  → file content unchanged
    - SNIPPET → content replaced by a representative excerpt
    - MAP   → content replaced by a structural map (definitions only)
    - SKIP  → file excluded entirely
    """
    from noxaudit.focus.base import extract_file_map, extract_file_snippets

    tier_map = {fc.path: fc.tier for fc in classified}
    enriched: list[FileContent] = []

    for f in files:
        tier = tier_map.get(f.path, ContentTier.SKIP)
        if tier == ContentTier.FULL:
            enriched.append(f)
        elif tier == ContentTier.SNIPPET:
            enriched.append(extract_file_snippets(f))
        elif tier == ContentTier.MAP:
            enriched.append(extract_file_map(f))
        # SKIP: not included

    return enriched


def run_prepass(
    files: list[FileContent],
    focus_names: list[str],
    provider,
) -> tuple[PrepassResult, list[FileContent]]:
    """Run pre-pass classification and return enriched files for the main audit.

    The provider classifies each file into a content tier using severity:
      high → full content, medium → snippet, low → structural map, no finding → skip

    Args:
        files: All files gathered for the audit.
        focus_names: Focus area names (e.g. ["security", "performance"]).
        provider: An initialised provider instance (AnthropicProvider, etc.).

    Returns:
        (PrepassResult, enriched_files) where enriched_files is the reduced
        file list with content tiered according to classification.
    """
    if not files:
        return PrepassResult(classified=[], original_count=0, retained_count=0), []

    print(f"  Pre-pass: classifying {len(files)} files...")
    prompt = build_classification_prompt(focus_names)

    # Run classification: findings encode the tier via severity
    classification_findings = provider.run_audit(files, prompt, "")

    # Build a tier map from the classification findings
    tier_map: dict[str, ContentTier] = {}
    reason_map: dict[str, str] = {}
    for finding in classification_findings:
        tier_map[finding.file] = _severity_to_tier(finding.severity.value)
        reason_map[finding.file] = finding.description

    # Build per-file classification results (files without findings → SKIP)
    classified = []
    for fc in files:
        tier = tier_map.get(fc.path, ContentTier.SKIP)
        reason = reason_map.get(fc.path)
        classified.append(FileClassification(path=fc.path, tier=tier, reason=reason))

    retained_count = sum(1 for fc in classified if fc.relevant)
    result = PrepassResult(
        classified=classified,
        original_count=len(files),
        retained_count=retained_count,
    )

    # Build enriched content for the main audit
    enriched = enrich_files(files, classified)
    print(
        f"  Pre-pass: {retained_count}/{len(files)} files retained "
        f"({sum(1 for fc in classified if fc.tier == ContentTier.FULL)} full, "
        f"{sum(1 for fc in classified if fc.tier == ContentTier.SNIPPET)} snippet, "
        f"{sum(1 for fc in classified if fc.tier == ContentTier.MAP)} map)"
    )

    return result, enriched
