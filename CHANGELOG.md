# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Renamed project from Nightwatch to Noxaudit for better GitHub uniqueness
- Package name changed from `nightwatch-ai` to `noxaudit`
- CLI command changed from `nightwatch` to `noxaudit`
- Configuration file renamed from `nightwatch.yml` to `noxaudit.yml`
- Working directory changed from `.nightwatch/` to `.noxaudit/`
- Made GitHub issue footer repository URL configurable via `repository_url` config field

## [0.1.0] - 2026-02-15

### Added
- Initial release
- Multi-provider AI support (Anthropic, Google Gemini)
- Rotating focus areas: security, patterns, docs, hygiene, performance, dependencies, testing
- Decision memory system to avoid re-flagging resolved issues
- GitHub Actions integration
- Telegram notifications
- GitHub issue creation
- Two-pass audit for large codebases
