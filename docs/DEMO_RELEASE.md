# Demo Release Preparation Guide

This guide helps you prepare Marcus for a demo/milestone release.

## 🎯 Current Goal: Get to Demo State

You want to:
1. Lock in all changes that work
2. Create a stable version for demos
3. Know exactly when to bump versions
4. Keep main branch stable

---

## 📋 Pre-Demo Checklist

### **Phase 1: Feature Freeze** (Start Here)

- [ ] **All feature branches merged to `develop`**
  ```bash
  # Check what's not merged
  git branch --no-merged develop
  ```

- [ ] **All tests passing on `develop`**
  ```bash
  pytest tests/ --cov=src --cov-fail-under=80
  mypy src/
  ```

- [ ] **All GitHub issues for demo milestone closed**
  - Check: https://github.com/lwgray/marcus/milestone/X

- [ ] **Security scan clean**
  ```bash
  bandit -r src/
  ```

### **Phase 2: Demo Testing** (Integration Testing)

- [ ] **Create release candidate branch**
  ```bash
  git checkout develop
  git checkout -b release/v0.2.0-rc1
  ```

- [ ] **Bump to RC version**
  ```bash
  ./scripts/bump-version.sh 0.2.0-rc1
  ```

- [ ] **Run full integration test suite**
  ```bash
  pytest tests/integration/ -v
  ```

- [ ] **Manual demo walkthrough**
  - [ ] Agent registration works
  - [ ] Project creation from plain English
  - [ ] Tasks created on Kanban board
  - [ ] Agents pull and complete tasks
  - [ ] Context flows between tasks
  - [ ] Progress reporting accurate
  - [ ] Blockers handled correctly
  - [ ] Multi-agent parallelization works

- [ ] **Docker build succeeds**
  ```bash
  docker build -t marcus:v0.2.0-rc1 .
  docker-compose up -d
  # Test MCP endpoints
  ```

- [ ] **Cato visualization working**
  ```bash
  cd /Users/lwgray/dev/cato
  ./cato start
  # Verify all views render correctly
  ```

### **Phase 3: Documentation & Polish**

- [ ] **Update CHANGELOG.md**
  - Move all items from `[Unreleased]` to `[0.2.0]`
  - Add today's date
  - Verify all changes documented

- [ ] **Update README.md**
  - [ ] Quick Start still accurate
  - [ ] Screenshots up to date
  - [ ] Version badges correct

- [ ] **Update documentation**
  - [ ] API docs reflect changes
  - [ ] Configuration examples current
  - [ ] Tutorial tested end-to-end

- [ ] **Create demo script/video**
  - [ ] Record walkthrough
  - [ ] Create demo.md with talking points

### **Phase 4: Release to Main**

- [ ] **Bump to final version**
  ```bash
  git checkout release/v0.2.0-rc1
  ./scripts/bump-version.sh 0.2.0
  git push origin release/v0.2.0-rc1
  ```

- [ ] **Create PR: release/v0.2.0-rc1 → main**
  ```bash
  # PR from release branch to main (version already bumped!)
  gh pr create --base main --head release/v0.2.0-rc1 \
    --title "Release v0.2.0 - Demo Ready" \
    --body "See CHANGELOG.md for details"
  ```

- [ ] **Get PR approval** (code review)

- [ ] **Merge to main**
  ```bash
  # GitHub will run version-gate workflow
  # Ensures version bumped and CHANGELOG updated
  ```

- [ ] **Verify tag created**
  ```bash
  git tag -l | grep v0.2.0
  ```

- [ ] **Push tag**
  ```bash
  git push origin v0.2.0
  ```

### **Phase 5: Publish & Deploy**

- [ ] **Publish Docker images**
  ```bash
  docker tag marcus:v0.2.0 lwgray/marcus:0.2.0
  docker tag marcus:v0.2.0 lwgray/marcus:latest
  docker push lwgray/marcus:0.2.0
  docker push lwgray/marcus:latest
  ```

- [ ] **Create GitHub Release**
  ```bash
  gh release create v0.2.0 \
    --title "v0.2.0 - Demo Ready Release" \
    --notes-file RELEASE_NOTES.md
  ```

- [ ] **Update Cato to matching version**
  ```bash
  cd /Users/lwgray/dev/cato
  git checkout -b release/v0.2.0
  # Update pyproject.toml to 0.2.0
  # Update CHANGELOG.md
  # Tag and release
  ```

### **Phase 6: Post-Release**

- [ ] **Back-merge to develop**
  ```bash
  git checkout develop
  git merge main --no-ff
  git push origin develop
  ```

- [ ] **Announce release**
  - [ ] Discord announcement
  - [ ] GitHub Discussions post
  - [ ] Update documentation site

- [ ] **Archive release branch**
  ```bash
  git branch -d release/v0.2.0
  git push origin --delete release/v0.2.0
  ```

---

## 🚦 When to Bump Versions (Trigger System)

### **Automatic Triggers:**

| Event | Action | Version Bump |
|-------|--------|--------------|
| **PR to `develop`** | No version bump needed | None |
| **PR to `main`** | ✅ **REQUIRED**: Version bump + CHANGELOG | MINOR (0.X.0) |
| **Hotfix to `main`** | ✅ **REQUIRED**: Version bump + CHANGELOG | PATCH (0.1.X) |
| **Breaking change** | Must document in PR | MINOR (pre-1.0) or MAJOR (post-1.0) |

### **Manual Triggers (You Decide):**

**Bump PATCH (0.1.X) when:**
- ✅ Bug fix only
- ✅ Security patch
- ✅ Documentation update
- ✅ No API changes

**Bump MINOR (0.X.0) when:**
- ✅ New feature added
- ✅ New MCP tool
- ✅ Breaking change (pre-1.0 only)
- ✅ Database schema change
- ✅ **DEMO READY** milestone reached ← **YOU ARE HERE**

**Bump MAJOR (X.0.0) when:**
- ✅ Stable 1.0 release
- ✅ Breaking API change (post-1.0)
- ✅ MCP protocol incompatibility

---

## 🛡️ Protection System

### **GitHub Actions (Automated)**
```
✅ version-gate.yml - Blocks merge if version not bumped
✅ test-suite.yml   - All tests must pass
✅ security-scan.yml - No critical vulnerabilities
```

### **Pre-commit Hooks (Local)**
```bash
# Install hooks
pre-commit install

# Runs automatically on git commit:
✅ black (formatting)
✅ isort (imports)
✅ mypy (type checking)
✅ pytest (unit tests)
```

### **Manual Gates**
- Code review required for PRs to `main`
- Two approvals for breaking changes
- Security review for auth/permissions changes

---

## 📊 Version Status Dashboard

**Current State:**
```
Marcus:  0.1.3.1 → 0.2.0 (demo target)
Cato:    2.0.0   → 0.2.0 (realign with Marcus)
```

**Next Steps:**
1. ✅ Finish validation system (Issue #170)
2. ✅ Merge feature branches to `develop`
3. ✅ Create `release/v0.2.0-rc1`
4. ✅ Test demo walkthrough
5. ✅ Bump to `0.2.0` and merge to `main`

---

## 🔄 Daily Workflow Reminder

```bash
# Working on features (day-to-day)
git checkout develop
git checkout -b feature/my-feature
# ... make changes ...
git commit -m "feat: add cool feature"
git push origin feature/my-feature
# Create PR to develop (no version bump needed)

# Getting ready for demo (milestone)
git checkout develop
git checkout -b release/v0.2.0-rc1
./scripts/bump-version.sh 0.2.0-rc1
# ... test everything ...
./scripts/bump-version.sh 0.2.0
# Create PR to main (version already bumped!)

# Hotfix in production
git checkout main
git checkout -b hotfix/critical-bug
# ... fix bug ...
./scripts/bump-version.sh patch  # 0.2.0 → 0.2.1
git push origin hotfix/critical-bug
# Create PR to main
```

---

## 🎬 Your Demo Scenario

**Goal:** Show Marcus coordinating multiple agents to build a todo app

**Before Demo:**
1. Marcus v0.2.0 running in Docker
2. Cato v0.2.0 visualization ready
3. Planka board with lists created
4. Test agent registered and ready

**Demo Flow:**
1. "Create a todo app with authentication"
2. Watch Marcus break into tasks
3. Watch agents pull and work on tasks
4. Show Cato visualization of coordination
5. Show completed code + passing tests

**Success Criteria:**
- ✅ All tasks complete without manual intervention
- ✅ Context flows between agents
- ✅ Cato shows beautiful visualization
- ✅ No errors or blockers during demo
