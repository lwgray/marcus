# Version Bump Quick Reference

## 🚨 When MUST I Bump Version?

### **ALWAYS Required:**
- ✅ **Before merging PR to `main`** (GitHub Action will block if not bumped)
- ✅ **Before creating a release** (release/* branches)
- ✅ **After a hotfix** (hotfix/* branches)

### **NEVER Required:**
- ❌ Merging PR to `develop`
- ❌ Working on feature branches
- ❌ Daily commits
- ❌ WIP changes

---

## 🎯 Which Version to Bump?

```
┌─────────────────────────────────────────────────────────┐
│  What did you change?                                   │
└─────────────────────────────────────────────────────────┘

📝 Bug fix only, no API changes
   └─> PATCH (0.1.X)
   └─> ./scripts/bump-version.sh patch

🎉 New feature, new tool, new capability
   └─> MINOR (0.X.0)
   └─> ./scripts/bump-version.sh minor

💥 Breaking change (after 1.0), major rewrite
   └─> MAJOR (X.0.0)
   └─> ./scripts/bump-version.sh major

🎬 Demo milestone, pre-release
   └─> CUSTOM (0.2.0-rc1)
   └─> ./scripts/bump-version.sh 0.2.0-rc1
```

---

## ⚡ Quick Commands

```bash
# Bump version automatically
./scripts/bump-version.sh patch   # 0.1.3 → 0.1.4
./scripts/bump-version.sh minor   # 0.1.3 → 0.2.0
./scripts/bump-version.sh major   # 0.1.3 → 1.0.0
./scripts/bump-version.sh 0.2.0-rc1  # Custom version

# What the script does:
# 1. Updates pyproject.toml
# 2. Updates CHANGELOG.md
# 3. Creates git commit
# 4. Creates git tag
# 5. Reminds you to push
```

---

## 📋 Version Bump Checklist

Before running `bump-version.sh`:

- [ ] All tests passing (`pytest`)
- [ ] Code formatted (`black .`, `isort .`)
- [ ] Type checks passing (`mypy src/`)
- [ ] CHANGELOG.md has entries under `[Unreleased]`
- [ ] On correct branch (`develop` for features, `release/*` for releases)

After running `bump-version.sh`:

- [ ] Review the changes (`git show HEAD`)
- [ ] Push commit (`git push origin BRANCH_NAME`)
- [ ] Push tag (`git push origin vX.X.X`)
- [ ] Update Cato if needed (coordinate versions)

---

## 🔄 Common Scenarios

### **Scenario 1: Finishing a Feature**
```bash
# You're on: feature/cool-feature
# Create PR to develop
gh pr create --base develop --head feature/cool-feature
# PR merges to develop
# ❌ NO version bump needed!
```

### **Scenario 2: Ready for Demo**
```bash
# You're on: develop (all features merged)
git checkout -b release/v0.2.0-rc1
./scripts/bump-version.sh 0.2.0-rc1
# Test everything...
./scripts/bump-version.sh 0.2.0
git push origin release/v0.2.0
# Create PR to main
# ✅ Version already bumped!
```

### **Scenario 3: Production Bug**
```bash
# You're on: main (v0.2.0)
git checkout -b hotfix/critical-bug
# Fix the bug...
./scripts/bump-version.sh patch  # → 0.2.1
git push origin hotfix/critical-bug
# Create PR to main
# ✅ Version bumped!
```

### **Scenario 4: Adding a Feature**
```bash
# You're on: feature/new-tool
# Finish coding...
git add .
git commit -m "feat: add new MCP tool"
git push origin feature/new-tool
# Create PR to develop
gh pr create --base develop
# PR merges to develop
# ❌ NO version bump!

# Later, when releasing all features from develop:
git checkout develop
git pull origin develop
git checkout -b release/v0.3.0
./scripts/bump-version.sh minor  # → 0.3.0
# Create PR from release/v0.3.0 to main
gh pr create --base main --head release/v0.3.0
# ✅ Version bumped!
```

---

## 🛡️ What Blocks You?

### **GitHub Action: version-gate.yml**

When you create PR to `main`, this checks:
- ✅ Version in `pyproject.toml` is newer than target branch
- ✅ `CHANGELOG.md` was updated
- ❌ **Blocks merge if either fails**

You'll see:
```
❌ Version Gate Check Failed

Before merging to main, you must:
- [ ] Bump version in pyproject.toml
- [ ] Update CHANGELOG.md
```

**Fix:**
```bash
# On your PR branch
./scripts/bump-version.sh minor
git push origin YOUR_BRANCH
# PR will re-check and pass ✅
```

---

## 📦 Coordinating Marcus + Cato

**Rule:** Cato MAJOR.MINOR should match Marcus

```bash
# Marcus going to 0.2.0?
cd /Users/lwgray/dev/marcus
./scripts/bump-version.sh 0.2.0

# Update Cato to match
cd /Users/lwgray/dev/cato
# Update pyproject.toml: version = "0.2.0"
# Update CHANGELOG.md
git commit -am "chore: bump version to 0.2.0 (match Marcus)"
git tag v0.2.0
git push origin main --tags
```

---

## 🎓 Semantic Versioning Summary

```
v0.2.1
  │ │ └─ PATCH: Bug fixes, no API change
  │ └─── MINOR: New features, can break (pre-1.0)
  └───── MAJOR: Breaking changes (post-1.0)

Pre-1.0:  Breaking changes OK in MINOR bumps
Post-1.0: Breaking changes only in MAJOR bumps
```

---

## 🚀 Your Current Mission

**Goal:** Get to v0.2.0 demo release

**Steps:**
1. Finish Issue #170 (validation system)
2. Merge feature branch to `develop`
3. Create `release/v0.2.0-rc1`
4. Test demo scenario
5. Bump to `0.2.0`
6. Merge to `main`
7. Celebrate! 🎉

**See:** [DEMO_RELEASE.md](DEMO_RELEASE.md) for full checklist
