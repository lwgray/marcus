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

[Unreleased]: https://github.com/lwgray/marcus/compare/v0.1.3.1...HEAD
[0.1.3.1]: https://github.com/lwgray/marcus/compare/v0.1.3...v0.1.3.1
[0.1.3]: https://github.com/lwgray/marcus/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/lwgray/marcus/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/lwgray/marcus/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lwgray/marcus/releases/tag/v0.1.0
