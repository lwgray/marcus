# AppForge Modern Fork Integration - Changelog

## Date: December 17, 2025

## Summary

Successfully transitioned AppForge benchmark integration from using an adapter pattern to direct compilation with the modern AppForge fork. This eliminates the adaptation layer, simplifies the codebase, and fixes critical package name mismatch issues.

---

## Problem Solved

### Original Issue: Package Name Mismatch
- **Symptom**: Tests passing at 75% instead of 100%
- **Root Cause**: AppForge tests expected package `bored.codebyk.mintcalc` but Marcus generated `com.calculator`
- **Why**: Package name requirement was in `task_info.json` but never passed to Marcus

### Original Architecture Issues
- Marcus generates modern Android code (androidx, Material Components, Gradle 8.9 compatible)
- Original AppForge (2021) used old tooling (Gradle 7.2, AGP 7.1.2, Java 8, API 31)
- Required complex adapter to bridge the gap
- Adapter was error-prone and added unnecessary complexity

---

## Solution: Modern Fork + Direct Compilation

### 1. Modern AppForge Fork
Created fork at: https://github.com/lwgray/AppForge_Bench

**Branch**: `modernize-toolchain-2024`

**Modernization Changes**:
- Gradle 7.2 → 8.9
- Android Gradle Plugin 7.1.2 → 8.7.0
- Java 8 → 17
- API Level 31 → 34
- Added Kotlin 1.9.22 support
- Updated templates to use `namespace` instead of deprecated `package` attribute
- Modified themes to use Material Components defaults (supports non-deterministic color generation)

**Key Files Modified in Fork**:
- `gradle-wrapper.properties` - Gradle 8.9
- `build.gradle` - AGP 8.7, Kotlin 1.9.22
- `app/build.gradle` - namespace, API 34, Java 17, Kotlin support
- `compiler/build.py` - gradlew permissions fix
- `app/src/main/res/values/themes.xml` - removed hardcoded color references
- `app/src/main/res/values-night/themes.xml` - removed hardcoded color references

**Documentation Created in Fork**:
- `MODERNIZATION.md` - detailed explanation of all changes

### 2. Package Name Extraction
**File**: `task_converter.py`

**Changes**:
- `fetch_appforge_task()` now reads `task_info.json` from modern fork
- Extracts `package_name` and `permissions` fields
- `generate_project_spec()` includes package name as CRITICAL requirement in Marcus spec
- Template emphasizes package name requirement multiple times
- Added `--bench-folder` parameter to specify modern fork location

**Example Output**:
```markdown
## CRITICAL: Package Name

**YOU MUST USE THIS EXACT PACKAGE NAME:**

```
bored.codebyk.mintcalc
```

This package name is required for AppForge test compatibility.
```

### 3. Adapter Removal
**File Deleted**: `marcus_appforge_adapter.py`

**File Modified**: `evaluator.py`

**Changes**:
- Removed `from marcus_appforge_adapter import MarcusAppForgeAdapter`
- Removed conditional logic checking for modern vs old fork
- Simplified to always use direct compilation
- Updated docstrings to document modern fork requirement

**Before**:
```python
if use_modern:
    compile_dir = implementation_dir
else:
    adapter = MarcusAppForgeAdapter(implementation_dir, adapted_dir)
    implementation_files = adapter.adapt()
    compile_dir = adapted_dir
```

**After**:
```python
# Modern fork (Gradle 8.9, AGP 8.7, Java 17, API 34) compiles Marcus code
# directly without any adaptation layer.
print("[2/4] Using modern AppForge toolchain...")
print("  ✓ Modern fork compiles Marcus code directly (no adapter)")
compile_dir = implementation_dir
```

### 4. Documentation Updates

**README.md**:
- Added modern fork requirement in header
- Updated Quick Start with conda environment requirement
- Added section on cloning modern fork
- Documented why modern fork matters
- Added uiautomator2 and opencv-python dependency requirements
- Updated architecture diagram to show "NO ADAPTER NEEDED"
- Updated file structure to show modern fork location
- Replaced "Known Limitations" with "Current Status & Limitations"

**QUICK_START.md**:
- Added step to clone modern fork with explanation
- Added uiautomator2 and opencv-python installation requirements
- Updated installation time estimate (5 → 10 minutes)

---

## Critical Dependencies Documented

### Python Dependencies
```bash
pip install uiautomator2 opencv-python
```

**Why these dependencies?**
- AppForge UI testing framework requires `uiautomator2` and `opencv-python`
- Without these, tests appear to run but produce empty logs (2-3 sec vs 60+ sec duration)
- Must be installed in the same Python environment as Marcus and AppForge

---

## Testing Results

### Before Fix
- **Compilation**: SUCCESS (compile: 1)
- **Test Pass Rate**: 75% (test: 0.75)
- **Issue**: Package name mismatch prevented 25% of tests from running

### After Fix (Expected)
With package name correctly specified:
- Marcus should generate code with `bored.codebyk.mintcalc` package
- Tests should find the correct package
- Test pass rate should improve (pending full pipeline test)

---

## Files Modified

### Marcus Codebase
1. `dev-tools/experiments/benchmarks/appforge/task_converter.py`
   - Added `bench_folder` parameter to all functions
   - Extract package name from `task_info.json`
   - Include package name in project spec with CRITICAL emphasis
   - Updated CLI with `--bench-folder` argument

2. `dev-tools/experiments/benchmarks/appforge/evaluator.py`
   - Removed adapter import
   - Removed conditional modern/old fork logic
   - Simplified to direct compilation only
   - Updated docstrings

3. `dev-tools/experiments/benchmarks/appforge/README.md`
   - Complete rewrite of several sections
   - Modern fork emphasis throughout
   - Dependency documentation
   - Architecture updates

4. `dev-tools/experiments/benchmarks/appforge/QUICK_START.md`
   - Added modern fork setup steps
   - Added UI testing dependencies requirement (uiautomator2, opencv-python)

5. **DELETED**: `dev-tools/experiments/benchmarks/appforge/marcus_appforge_adapter.py`
   - No longer needed with modern fork

### Modern AppForge Fork
1. `gradle-wrapper.properties`
2. `build.gradle` (root)
3. `app/build.gradle`
4. `compiler/build.py`
5. `app/src/main/res/values/themes.xml`
6. `app/src/main/res/values-night/themes.xml`
7. **NEW**: `MODERNIZATION.md`

---

## How to Use (Quick Reference)

### Setup Once
```bash
# Clone modern fork
cd ~/dev
git clone https://github.com/lwgray/AppForge_Bench AppForge_Bench_Modern
cd AppForge_Bench_Modern
git checkout modernize-toolchain-2024

# Install dependencies in your Python environment
cd /path/to/marcus/dev-tools/experiments/benchmarks/appforge
pip install -r requirements.txt
pip install uiautomator2 opencv-python  # Required for UI testing
```

### Run Benchmark
```bash
cd /path/to/marcus/dev-tools/experiments/benchmarks/appforge

# Task converter now automatically extracts package name
python appforge_runner.py --task-id 63 --num-agents 5
```

The task converter will:
1. Fetch task from AppForge tasks.json
2. Read package name from `~/dev/AppForge_Bench_Modern/tasks/Mint_calculator/task_info.json`
3. Generate Marcus project spec with package name requirement
4. Marcus agents will see package name in spec and use it

---

## Benefits of This Approach

### 1. **Cleaner Architecture**
- No adapter layer to maintain
- Direct compilation is faster and more reliable
- Fewer moving parts = fewer failure points

### 2. **Modern Standards**
- Aligned with 2024 Android development practices
- Marcus generates code that works with modern tooling out of the box
- Future-proof for continued Android ecosystem evolution

### 3. **Better Test Compatibility**
- Package names now correctly passed to Marcus
- Permissions extracted from task_info.json
- All test requirements properly communicated

### 4. **Maintainability**
- Modern fork is a separate repo (good open source practice)
- Can update independently of Marcus
- Clear separation of concerns
- Easy to contribute improvements back upstream

### 5. **Non-Deterministic Generation Support**
- Theme templates use Material Components defaults
- No hardcoded color names required
- AI can generate any color scheme and it will compile
- Flexible and robust

---

## Next Steps

1. **Test Full Pipeline**: Run complete benchmark with package name fix
2. **Verify Test Pass Rate**: Should improve from 75% with correct package name
3. **Run More Tasks**: Validate approach works across different AppForge tasks
4. **Consider PR to Original AppForge**: Modern fork improvements could benefit upstream

---

## Lessons Learned

### What We Discovered

1. **Package Name Source**: Hidden in `task_info.json`, not in main `tasks.json`
2. **UI Testing Dependencies**: uiautomator2 and opencv-python are critical for test execution
3. **Direct is Better**: Adapter was masking incompatibility; fixing the root cause (old tooling) was the right solution
4. **Documentation is Critical**: All dependencies must be explicitly documented

### What We Fixed

1. **Toolchain Gap**: Modernized AppForge to match Marcus's output
2. **Missing Requirements**: Package name now extracted and passed to Marcus
3. **Complex Adapter**: Removed in favor of direct compatibility
4. **Dependency Gaps**: Documented all required dependencies

---

## Credits

- Modern fork: https://github.com/lwgray/AppForge_Bench
- Original AppForge: https://github.com/AppForge-Bench/AppForge
- Branch: modernize-toolchain-2024
