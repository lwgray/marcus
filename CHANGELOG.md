# Changelog

All notable changes to Marcus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security

## [0.2.0] - 2026-03-16
### Added
- Feature completeness validation system with AI-powered analysis (GH-170)
- Centralized configuration system with validation and environment support (GH-162)
- Composition-aware task completeness validation (GH-160)
- Composition-aware PRD extraction with specificity detection (GH-159)
- AI-powered task completeness validation with automatic retry
- Project management utilities and telemetry planning tools (GH-167)
- Demo materials: presentation decks, scripts, and audio transcriptions
- Single-agent trial runner for controlled experiments
- Enhanced task classifier with weighted signal scoring and confidence levels
- Protection for integration requirements from complexity filtering (GH-163)
- WorkAnalyzer for source code validation
- Pre-completion validation checks to agent workflow
- Hybrid test discovery strategy for validation

### Changed
- Simplified validation to single-tier intent system (GH-166)
- Simplified MCP tool logger to activity tracker (GH-164)
- Task completeness validator is now AI provider-agnostic
- Agent retry wait times reduced for better parallelization (GH-177)
- Integrated Marcus error framework and resilience patterns into validation

### Removed
- Integration requirements extraction from PRD analysis (GH-165)
- Duplicate documentation enhancement call in NLP pipeline

### Fixed
- Task classifier misclassification causing phase enforcement failures (GH-180)
- Strong signals (task name + labels) now override weak signals (description keywords)
- Database connection tasks correctly classified as IMPLEMENTATION vs INFRASTRUCTURE
- Code comment tasks correctly classified as DOCUMENTATION vs IMPLEMENTATION
- Config loading and project-local database path with tilde expansion (GH-171)
- MCP tool logging and workflow enforcement (GH-172)
- Validation retry tracking order to prevent premature blocker creation
- Code review issues from validation refactoring
- Security and code quality issues across codebase

## [0.1.3.1] - 2026-03-09
### Fixed
- Validation retry tracking order to prevent premature blocker creation (GH-170)

## [0.1.3] - 2026-03-08
### Fixed
- Security and code quality issues
- Validation system final updates (GH-170)
- Task label fetching from Kanban to use filtered labels

### Added
- Comprehensive resolution summary for Issue #170
- Pre-completion validation checks to agent workflow
- Runtime test execution to catch configuration issues
- Detailed logging to validation gate

## [0.1.2] - 2026-03-07
### Added
- Hybrid test discovery strategy for validation
- WorkAnalyzer for source code validation (GH-170)
- Phase 2 validation gate integration (GH-170)
- Retry tracking with comprehensive tests

### Changed
- Integrated Marcus error framework and resilience patterns into validation

## [0.1.1] - 2026-03-06
### Added
- Initial validation system framework
- Basic task completion verification

### Fixed
- Various bug fixes in agent coordination

## [0.1.0] - 2026-03-01
### Added
- Initial beta release
- Multi-agent coordination platform
- MCP protocol support
- GitHub and Planka Kanban integrations
- Agent registration and task assignment
- Context sharing through artifacts
- Progress reporting system
- Blocker handling workflow

[Unreleased]: https://github.com/lwgray/marcus/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/lwgray/marcus/compare/v0.1.3.1...v0.2.0
[0.1.3.1]: https://github.com/lwgray/marcus/compare/v0.1.3...v0.1.3.1
[0.1.3]: https://github.com/lwgray/marcus/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/lwgray/marcus/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/lwgray/marcus/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lwgray/marcus/releases/tag/v0.1.0
