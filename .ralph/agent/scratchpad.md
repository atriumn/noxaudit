# Scratchpad: Rename nightwatch → noxaudit

## Objective
Rename nightwatch to noxaudit and prepare for open source release. The name "nightwatch" is too common on GitHub (~1M repos), so we're renaming to "noxaudit" (nox = night in Latin).

## Current Understanding
- Python package: `nightwatch/` → needs to be `noxaudit/`
- Config file: `nightwatch.yml` → `noxaudit.yml`
- CLI command: `nightwatch` → `noxaudit`
- PyPI package: `nightwatch-ai` → `noxaudit`
- GitHub repo: atriumn/nightwatch → atriumn/noxaudit
- Directory: `.nightwatch/` → `.noxaudit/`

## Repository Structure
```
nightwatch/              # Main Python package
├── focus/               # Focus area implementations
├── providers/           # AI provider integrations
└── notifications/       # Notification handlers
tests/                   # Test suite
action/                  # GitHub Action definition
focus_prompts/           # Prompt templates
pyproject.toml          # Package metadata
nightwatch.yml.example  # Config example
```

## Task Breakdown

### Phase 1: Core Renaming
1. Rename Python package directory: `nightwatch/` → `noxaudit/`
2. Update all Python imports across codebase
3. Update pyproject.toml (package name, scripts, URLs)
4. Rename config example file
5. Update .gitignore

### Phase 2: Content Updates
6. Update all Python files (docstrings, comments, hardcoded strings)
7. Update all Markdown files (README, focus prompts)
8. Update YAML files (GitHub Action, workflows)
9. Make issues footer configurable

### Phase 3: Documentation
10. Create CONTRIBUTING.md
11. Create CHANGELOG.md
12. Update README.md

### Phase 4: Verification
13. Test package installation
14. Run test suite
15. Run linters
16. Verify no old references remain

## Progress
- [x] Task 1: Renamed nightwatch/ → noxaudit/ (committed: f85f095)
- [x] Task 2: Update pyproject.toml (committed: 2fe1e0d)
  - Package name: nightwatch-ai → noxaudit
  - CLI entry point: nightwatch → noxaudit
  - GitHub URLs updated
  - Package reference in hatch config updated
- [x] Task 3: Update Python imports (committed: d6dab14)
  - Updated all imports in noxaudit/ package files
  - Updated all imports in tests/ files
  - 26 files changed, 54 imports updated
  - All imports now use noxaudit.* instead of nightwatch.*
- [x] Task 4: Rename config file and update .gitignore (committed: 872c3ef)
  - Renamed nightwatch.yml.example → noxaudit.yml.example
  - Updated config header and path references (.nightwatch/ → .noxaudit/)
  - Updated default labels from nightwatch to noxaudit
  - Added .noxaudit/ and noxaudit.yml to .gitignore
  - Kept legacy entries for backward compatibility
- [x] Task 5: Update GitHub Action and CI workflow (committed: 8929216)
  - Updated action/action.yml: name, description, config defaults, install URL
  - Updated all directory paths from .nightwatch/ to .noxaudit/
  - Updated cache keys and artifact names
  - Updated CLI commands from nightwatch to noxaudit
  - Updated .github/workflows/ci.yml: ruff check commands to use noxaudit/

## Current Task
All tasks completed! Ready for final review.

## Latest Completed
- [x] Task 10: Verify package install ✓
  - Package installs successfully with uv
  - CLI command `noxaudit` works correctly (--help, schedule)
  - All Python imports work (cli, runner, config modules)
  - No import errors detected
- [x] Task 11: Run tests and linters ✓
  - All 91 tests pass (pytest tests/ -v)
  - Ruff linter passes (ruff check noxaudit/ tests/)
  - Code formatting verified (ruff format --check)
  - No remaining nightwatch references (except intentional: CHANGELOG, keywords)
  - README verified to use correct commands and branding
- [x] Task 9: Create CHANGELOG.md (committed: 61856d0)
  - Added CHANGELOG.md following Keep a Changelog format
  - Documents rename from nightwatch to noxaudit
  - Lists all breaking changes (package name, CLI, config file, directory)
  - Documents initial 0.1.0 release features
- [x] Task 8: Create CONTRIBUTING.md (committed: 5cdeee9)
  - Added comprehensive contributing guide
  - Covers development setup, testing, code quality
  - Includes guide for adding new focus areas
  - Documents project structure and PR guidelines
- [x] Task 7: Make issues footer configurable and fix remaining nightwatch refs (committed: ba3f606)
  - Added repository_url field to IssuesConfig (default: https://github.com/atriumn/noxaudit)
  - Updated issues.py to use configurable URL in footer
  - Fixed all hardcoded "nightwatch" references in issues module:
    - Issue title prefix, finding markers, labels all now use "noxaudit"
  - Renamed NightwatchConfig → NoxauditConfig class
  - Updated all default paths from .nightwatch/ to .noxaudit/
  - Updated default labels from "nightwatch" to "noxaudit"
  - Updated config file references from nightwatch.yml to noxaudit.yml
  - Updated CLI help text and command messages
  - Updated all test files to use new class and config names
  - Updated all runner.py type annotations and file paths
  - Updated docstrings and comments across codebase

## Remaining Tasks
None - all tasks completed!

## Summary
✅ **OBJECTIVE COMPLETE**: Renamed nightwatch → noxaudit for open source release

All 9 commits pushed to branch `refactor/design-and-implement-nightwatch-nightly-1`:
1. f85f095: Rename nightwatch/ directory to noxaudit/
2. 2fe1e0d: Update pyproject.toml for noxaudit rename
3. d6dab14: Update all Python imports from nightwatch to noxaudit
4. 872c3ef: Rename config file and update .gitignore
5. 8929216: Update GitHub Action and CI workflow for noxaudit rename
6. a03dca8: Update README.md with Noxaudit branding
7. ba3f606: Make issues footer configurable and fix remaining nightwatch refs
8. 5cdeee9: Add CONTRIBUTING.md for open source contributors
9. 61856d0: Add CHANGELOG.md documenting rename and initial release

## Verification Results
✅ All 91 tests pass
✅ Ruff linter passes
✅ Code formatting verified
✅ Package installs successfully
✅ CLI command `noxaudit` works
✅ All Python imports functional
✅ No unwanted nightwatch references remain

## Notes
- This is a pure refactor - no functional changes
- All references updated atomically across 9 commits
- Tests/lint pass - ready for PR
