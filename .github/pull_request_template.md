# Pull Request

> **PyCon 2026 Sprint contributor?** Welcome! Fill this out and a maintainer will review within the sprint day.

## Description

<!-- One paragraph. What problem does it solve? What did you change? -->

**What does this PR do?**


**Why is this change needed?**


**Related Issue(s):**

Fixes #(issue number)

---

## 📸 Proof: Marcus ran on my machine

<!--
REQUIRED for code PRs. Exempt for docs-only changes (typos, rewording, .rst edits).

Run `./marcus start` then `./marcus status` in your terminal.
Paste a screenshot of the output here.

PRs without this section filled in will not be reviewed.
-->

_Replace this line with your screenshot or terminal output._

---

## Type of Change

<!-- Check all that apply -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test updates or additions
- [ ] 🔧 Configuration/build changes

## Branch Information

<!-- Verify your branch setup -->

- [ ] This PR targets the `develop` branch (not `main`)
- [ ] My branch is up-to-date with `upstream/develop`
- [ ] I'm working in my fork's feature branch
- [ ] I've synced with upstream to avoid conflicts

## Changes Made

<!-- Provide a bullet-point list of key changes -->

-
-
-

## Testing

<!-- Describe how you tested your changes -->

**Unit Tests:**

- [ ] All existing tests pass (`pytest`)
- [ ] I have added tests for my changes
- [ ] Test coverage is ≥80% for new code

**Integration Tests:**

- [ ] Integration tests pass (if applicable)
- [ ] I have tested with external services (Planka/GitHub/etc.) if applicable

**Manual Testing:**

Describe what manual testing you performed:

-
-

**Test Environment:**

- OS: [e.g., macOS 13, Ubuntu 22.04]
- Python Version: [e.g., 3.11.5]
- Running via: [Docker / Local Python]

## Code Quality

<!-- Verify all quality checks pass -->

- [ ] All pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] MyPy type checking passes (`mypy src/`)
- [ ] Code is formatted with Black (`black src/`)
- [ ] Imports are organized with isort (`isort src/`)
- [ ] Ruff linting passes (`ruff check src/`)
- [ ] No secrets detected (`detect-secrets scan`)
- [ ] My code follows the project's style guidelines

## Documentation

<!-- Verify documentation is updated -->

- [ ] I have updated relevant documentation in `docs/`
- [ ] I have added NumPy-style docstrings to new functions/classes
- [ ] I have updated CHANGELOG.md (if user-facing change)
- [ ] Code comments explain complex logic or decisions
- [ ] README.md updated (if needed)

**Documentation Changes:**

<!-- List what documentation was updated -->

-
-

## Backwards Compatibility

<!-- For breaking changes or deprecations -->

- [ ] This change maintains backwards compatibility
- [ ] This change includes breaking changes (described below)
- [ ] This change follows the deprecation process (if applicable)

**Breaking Changes** (if any):


**Migration Guide** (if needed):


## Screenshots / Demos

<!-- For UI changes or new features, include screenshots or GIFs -->

**Before:**


**After:**


## Performance Impact

<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Performance improved
- [ ] Potential performance impact (described below)

**Performance Notes:**


## Dependencies

<!-- List any new dependencies or version changes -->

- [ ] No new dependencies added
- [ ] New dependencies added (listed below)

**New Dependencies:**


## Checklist

<!-- Final verification before submitting -->

- [ ] I have read the [CONTRIBUTING.md](../CONTRIBUTING.md) guide
- [ ] My code follows the project's code style
- [ ] I have performed a self-review of my code
- [ ] I have commented complex code, particularly hard-to-understand areas
- [ ] I have made corresponding changes to documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Additional Notes

<!-- Any additional information for reviewers -->

**Reviewer Focus Areas:**

<!-- What should reviewers pay special attention to? -->

-
-

**Open Questions:**

<!-- Any uncertainties or decisions you'd like input on? -->

-
-

## Post-Merge Actions

<!-- What needs to happen after this is merged? -->

- [ ] Update deployment documentation
- [ ] Notify users of breaking changes
- [ ] Update related issues
- [ ] Other: ___________

---

## For Maintainers

<!-- Maintainers: Check these before merging -->

- [ ] Code review completed
- [ ] All CI checks pass
- [ ] Documentation is adequate
- [ ] Breaking changes properly communicated
- [ ] Ready to merge to `develop`
