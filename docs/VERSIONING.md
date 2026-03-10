# Marcus Versioning System

**Complete guide to knowing when and how to bump versions.**

---

## 📚 Quick Links

- **[Quick Reference Card](VERSION_QUICK_REF.md)** - Fast answers to "when do I version?"
- **[Demo Release Checklist](DEMO_RELEASE.md)** - Full process for getting to demo state
- **[CHANGELOG](../CHANGELOG.md)** - All version history

---

## 🎯 Your Current Mission

**Goal:** Get Marcus to v0.2.0 demo-ready state

**Current Status:**
```
✅ Marcus:  0.1.3.1 (synced with git tags)
✅ Cato:    0.1.1 (aligned with Marcus)
✅ CHANGELOG.md created
✅ Version bump automation created
✅ GitHub Action gates created
⏳ Next: Finish Issue #170 → Test → Release v0.2.0
```

---

## 🚦 The Answer: When Do I Version?

### **Simple Rule:**

```
┌─────────────────────────────────────────────────┐
│  Merging to main? → Version bump REQUIRED       │
│  Merging to develop? → NO version bump          │
│  Working on feature? → NO version bump          │
└─────────────────────────────────────────────────┘
```

### **Automated Enforcement:**

✅ **GitHub Action blocks merges to `main` unless:**
- Version in `pyproject.toml` is newer than `main`
- `CHANGELOG.md` was updated in the PR

❌ **You'll see this error if you forget:**
```
❌ Version Gate Check Failed

Before merging to main, you must:
- [ ] Bump version in pyproject.toml
- [ ] Update CHANGELOG.md
```

**Fix:** Run `./scripts/bump-version.sh minor` on your PR branch

---

## 🔄 Versioning Workflow

### **Day-to-Day Development (No Versioning)**

```bash
# Working on features - PRs go to develop
feature/my-feature ──PR──> develop  ❌ NO VERSION BUMP
feature/other      ──PR──> develop  ❌ NO VERSION BUMP
```

### **Release Preparation (Version Bump)**

```bash
# Ready for demo/release - develop goes to main via release branch
develop ──> release/v0.2.0-rc1  # Test version
  └─> bump to 0.2.0-rc1
  └─> test everything
  └─> bump to 0.2.0
  └─> PR to main  ✅ VERSION BUMPED (only when going to main!)
```

### **Hotfix (Version Bump)**

```bash
# Production bug
main ──> hotfix/critical-bug
  └─> fix bug
  └─> bump version (patch)
  └─> PR to main  ✅ VERSION BUMPED
```

---

## 🛠️ Tools You Have

### **1. Version Bump Script**

```bash
./scripts/bump-version.sh patch   # 0.1.3 → 0.1.4
./scripts/bump-version.sh minor   # 0.1.3 → 0.2.0
./scripts/bump-version.sh major   # 0.1.3 → 1.0.0
./scripts/bump-version.sh 0.2.0-rc1  # Custom
```

**What it does:**
- ✅ Updates `pyproject.toml`
- ✅ Updates `CHANGELOG.md` (moves Unreleased → versioned)
- ✅ Creates git commit
- ✅ Creates git tag
- ✅ Reminds you to push

### **2. GitHub Action (Automatic Gate)**

**File:** `.github/workflows/version-gate.yml`

**Triggers:** On PR to `develop` or `main`

**Checks:**
- Version in PR > version in target branch
- CHANGELOG.md was modified
- Blocks merge if fails

### **3. Pre-commit Hooks (Local Reminders)**

**File:** `.pre-commit-config.yaml`

**Reminders:**
- On `release/*` or `hotfix/*` branches → "Did you bump version?"
- If `src/` changed but not `CHANGELOG.md` → "Did you update CHANGELOG?"

**Install:**
```bash
pre-commit install
```

### **4. CHANGELOG.md**

**Format:** [Keep a Changelog](https://keepachangelog.com/)

**Structure:**
```markdown
## [Unreleased]
### Added
- New features go here during development

## [0.2.0] - 2026-03-15
### Added
- Features that shipped in 0.2.0
```

**Rule:** Always add changes to `[Unreleased]` first

---

## 📊 Semantic Versioning (SemVer)

### **Format:** `MAJOR.MINOR.PATCH`

```
v0.2.1
  │ │ └─ PATCH: Bug fixes, security patches
  │ └─── MINOR: New features, breaking changes (pre-1.0)
  └───── MAJOR: Breaking changes (post-1.0), stable releases
```

### **Pre-1.0 Rules (Current):**

- **PATCH (0.1.X):** Bug fixes only
- **MINOR (0.X.0):** New features + breaking changes allowed
- **MAJOR (X.0.0):** Reserved for 1.0 stable release

### **Post-1.0 Rules (Future):**

- **PATCH (1.0.X):** Bug fixes only
- **MINOR (1.X.0):** New features, backward compatible
- **MAJOR (X.0.0):** Breaking changes only

---

## 🔗 Marcus + Cato Coordination

**Rule:** Cato MAJOR.MINOR matches Marcus it supports

```
Marcus 0.1.x ←→ Cato 0.1.x
Marcus 0.2.x ←→ Cato 0.2.x
Marcus 1.0.x ←→ Cato 1.0.x
```

**When Marcus releases:**
1. Release Marcus first
2. Update Cato to matching MAJOR.MINOR
3. Release Cato

**Independent patches allowed:**
- Marcus 0.2.0 + Cato 0.2.1 ✅ (dashboard-only fix)
- Marcus 0.2.1 + Cato 0.2.0 ✅ (backend-only fix)

---

## 🎬 Your Demo Release Process

### **Phase 1: Feature Complete**
- [ ] Merge all feature branches to `develop`
- [ ] All tests passing
- [ ] All issues closed

### **Phase 2: Release Candidate**
```bash
git checkout develop
git checkout -b release/v0.2.0-rc1
./scripts/bump-version.sh 0.2.0-rc1
# Test demo walkthrough
```

### **Phase 3: Final Release**
```bash
# On release/v0.2.0-rc1
./scripts/bump-version.sh 0.2.0
git push origin release/v0.2.0
# Create PR to main
```

### **Phase 4: Publish**
- PR merges to `main`
- Tag automatically created
- Push tag: `git push origin v0.2.0`
- Publish Docker images
- Create GitHub release

**See:** [DEMO_RELEASE.md](DEMO_RELEASE.md) for full checklist

---

## 📋 Version Decision Tree

```
┌─────────────────────────────────────────┐
│  What are you doing?                    │
└─────────────────────────────────────────┘
         │
         ├─ Working on feature branch
         │  └─> ❌ NO VERSION BUMP
         │
         ├─ Merging PR to develop
         │  └─> ❌ NO VERSION BUMP
         │
         ├─ Creating release for demo/milestone
         │  └─> ✅ MINOR bump (0.X.0)
         │  └─> Run: ./scripts/bump-version.sh minor
         │
         ├─ Fixing bug in production
         │  └─> ✅ PATCH bump (0.1.X)
         │  └─> Run: ./scripts/bump-version.sh patch
         │
         └─ Releasing v1.0 stable
            └─> ✅ MAJOR bump (X.0.0)
            └─> Run: ./scripts/bump-version.sh major
```

---

## 🚨 Common Mistakes & Fixes

### **Mistake 1: Forgot to bump version before PR to main**

**Symptom:** GitHub Action blocks your PR

**Fix:**
```bash
# On your PR branch
./scripts/bump-version.sh minor
git push origin YOUR_BRANCH
# Action re-runs and passes ✅
```

### **Mistake 2: Bumped version on wrong branch**

**Symptom:** Version bumped on `feature/*` branch

**Fix:**
```bash
# Undo last commit (keeps changes)
git reset HEAD~1
# Move to correct branch
git checkout release/vX.X.X
git cherry-pick <commit-hash>
```

### **Mistake 3: CHANGELOG not updated**

**Symptom:** GitHub Action blocks your PR

**Fix:**
```bash
# Edit CHANGELOG.md manually or re-run:
./scripts/bump-version.sh <same-version>
# It will update CHANGELOG.md
```

### **Mistake 4: Version out of sync with git tags**

**Symptom:** `pyproject.toml` shows 0.1.0 but tags show v0.1.3

**Fix:**
```bash
# Check latest tag
git tag -l | sort -V | tail -1

# Sync pyproject.toml
./scripts/bump-version.sh <latest-tag-version>
```

---

## 📖 Examples

### **Example 1: Adding a Feature**

```bash
# Day 1-5: Development
git checkout develop
git checkout -b feature/new-mcp-tool
# ... code, commit, push ...
gh pr create --base develop
# PR merges - NO VERSION BUMP ✅
```

### **Example 2: Preparing Demo**

```bash
# All features done, ready to release
git checkout develop
git pull origin develop
git checkout -b release/v0.2.0

# Bump to RC for testing
./scripts/bump-version.sh 0.2.0-rc1
# Test demo walkthrough...

# Bump to final
./scripts/bump-version.sh 0.2.0

# Create PR to main
gh pr create --base main --head release/v0.2.0
# PR merges - VERSION BUMPED ✅

# Push tag
git checkout main
git pull
git push origin v0.2.0
```

### **Example 3: Production Hotfix**

```bash
# Critical bug in production
git checkout main
git checkout -b hotfix/security-patch

# Fix bug
# ... code ...

# Bump patch version
./scripts/bump-version.sh patch  # 0.2.0 → 0.2.1

# Create PR to main
gh pr create --base main --head hotfix/security-patch
# PR merges - VERSION BUMPED ✅

# Back-merge to develop
git checkout develop
git merge main
git push origin develop
```

---

## 🎓 Summary

### **Remember:**
1. ✅ **Only version when merging to `main`**
2. ✅ **Use `./scripts/bump-version.sh`** (automates everything)
3. ✅ **GitHub Action enforces rules** (can't forget)
4. ✅ **Keep Cato aligned with Marcus**

### **Quick Commands:**
```bash
# Bump version
./scripts/bump-version.sh [patch|minor|major|custom]

# Check current version
grep '^version = ' pyproject.toml

# See version history
git tag -l | sort -V

# View CHANGELOG
cat CHANGELOG.md
```

### **Quick Links:**
- [Quick Reference](VERSION_QUICK_REF.md) - Fast answers
- [Demo Checklist](DEMO_RELEASE.md) - Release process
- [CHANGELOG](../CHANGELOG.md) - Version history

---

**You're ready! 🚀 Focus on building features, the system handles versioning.**
