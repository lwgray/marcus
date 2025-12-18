# Format Conversion: Marcus → AppForge

## The Problem

**Marcus generates:** Full Android project directory structure
```
implementation/
├── app/
│   ├── src/main/java/com/example/app/MainActivity.java
│   ├── src/main/res/layout/activity_main.xml
│   ├── src/main/res/values/strings.xml
│   ├── build.gradle
│   └── ...
├── build.gradle
├── settings.gradle
└── README.md
```

**AppForge expects:** Either
1. JSON dict of file changes: `{"MainActivity.java": "...", "activity_main.xml": "..."}`
2. OR a folder path (has `compile_folder()` method!)

## Discovered: AppForge Already Supports Folders!

From `appforge.py:240-252`:
```python
def compile_folder(self, folder: Path, task_id: int):
    """
    Copy files from target folder and compile the application.
    """
    changed = compare_folder(folder, self.template_folder / 'empty_activity')
    return self.compile_json_based_on_template(changed, task_id)
```

**This is perfect!** AppForge can:
1. Take a folder (Marcus's `implementation/` directory)
2. Compare it to their empty template
3. Extract the differences
4. Compile it

## The `compare_folder` Function

From `utils.py:52-93`:
```python
def compare_folder(folderA: Path, folderB: Path) -> dict[str, str]:
    """
    Compare two folders and return files that differ or are new.

    Returns dict where:
    - keys are relative file paths
    - values are file contents
    """
    changed = {}
    for root, _dirs, files in os.walk(folderA):
        for name in files:
            p = Path(root) / name
            rel = str(p.relative_to(folderA))
            src_file = folderB / rel

            try:
                new_text = p.read_text(encoding="utf-8")
            except Exception:
                continue  # Skip binary files

            if not src_file.exists():
                changed[rel] = new_text  # New file
            else:
                old_text = src_file.read_text(encoding="utf-8")
                if new_text != old_text:
                    changed[rel] = new_text  # Modified file

    return changed
```

## Three Integration Options

### Option A: Use AppForge's `compile_folder()` Directly ✅ RECOMMENDED

**Pros:**
- ✅ Simplest - just pass Marcus's output directory
- ✅ No format conversion needed
- ✅ Uses AppForge's native comparison logic
- ✅ Handles binary files correctly (skips them)
- ✅ Works with Marcus's full project structure

**Cons:**
- None!

**Implementation:**
```python
from AppForge import AppForge

# Initialize AppForge
evaluator = AppForge(
    runs=f"marcus_task_{task_id}",
    base_folder=Path.home() / "appforge_benchmarks" / "runs",
    use_docker=True,
    docker_name='zenithfocuslight/appforge:latest'
)

# Marcus generates to: exp_dir / "implementation"
implementation_dir = exp_dir / "implementation"

# Compile using AppForge (it handles comparison internally)
compile_error = evaluator.compile_folder(implementation_dir, task_id)

if compile_error:
    print(f"Compilation failed: {compile_error}")
else:
    # Run tests
    result = evaluator.test(task_id)
    print(f"Test result: {result}")

# Cleanup
evaluator.clean_up()
```

---

### Option B: Manual Comparison + JSON Format

**Pros:**
- More control over what gets included
- Can filter/transform files before submission

**Cons:**
- ❌ Duplicates AppForge's `compare_folder` logic
- ❌ Need to handle template location
- ❌ More code to maintain
- ❌ More error-prone

**Implementation:**
```python
from AppForge import AppForge
from AppForge.utils import compare_folder

evaluator = AppForge(...)

# Manual comparison
template_path = Path.home() / "dev" / "AppForge" / "compiler" / "templates" / "empty_activity"
changed = compare_folder(implementation_dir, template_path)

# Compile using JSON
compile_error = evaluator.compile_json_based_on_template(changed, task_id)
```

**Verdict:** No advantage over Option A

---

### Option C: Build APK First, Then Test ❌ NOT RECOMMENDED

**Pros:**
- None

**Cons:**
- ❌ Marcus would need to run `gradlew assembleDebug` itself
- ❌ Requires Android SDK installed on Marcus machine
- ❌ More complex setup
- ❌ Defeats purpose of AppForge's compilation checking
- ❌ Lose AppForge's compile error feedback

**Verdict:** Don't do this

---

## Directory Structure Mapping

### AppForge Template (Empty):
```
empty_activity/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── AndroidManifest.xml
│   │   │   └── res/
│   │   │       ├── layout/activity_main.xml
│   │   │       ├── values/strings.xml
│   │   │       └── ...
│   │   ├── androidTest/...
│   │   └── test/...
│   └── build.gradle
├── build.gradle
├── settings.gradle
└── gradle/...
```

### Marcus Output (Should Match):
```
implementation/
├── app/
│   ├── src/
│   │   └── main/
│   │       ├── java/com/example/app/MainActivity.java  ← NEW
│   │       ├── AndroidManifest.xml                      ← MODIFIED
│   │       └── res/
│   │           ├── layout/activity_main.xml            ← MODIFIED
│   │           ├── values/strings.xml                  ← MODIFIED
│   │           └── ...
│   └── build.gradle                                      ← MODIFIED
├── build.gradle
└── settings.gradle
```

**AppForge's `compare_folder` will detect:**
- New: `app/src/main/java/com/example/app/MainActivity.java`
- Modified: `AndroidManifest.xml`, `activity_main.xml`, `strings.xml`, `build.gradle`
- Result: JSON dict with only these files

---

## Potential Issues & Solutions

### Issue 1: Marcus Project Structure Doesn't Match Template

**Symptom:** Marcus creates `/implementation/MyApp/app/...` instead of `/implementation/app/...`

**Solution:** Point to the correct subdirectory
```python
# Find the actual project root
project_root = implementation_dir
if (implementation_dir / "app").exists():
    project_root = implementation_dir
else:
    # Look for subdirectory containing app/
    for subdir in implementation_dir.iterdir():
        if subdir.is_dir() and (subdir / "app").exists():
            project_root = subdir
            break

compile_error = evaluator.compile_folder(project_root, task_id)
```

### Issue 2: Package Name Mismatch

**Symptom:** Marcus uses `com.marcus.generated` but AppForge expects task-specific package

**Solution:** AppForge's template is generic - it will accept any package name. Just ensure Marcus generates valid Android package structure:
```
app/src/main/java/com/whatever/package/MainActivity.java
```

### Issue 3: Missing Gradle Files

**Symptom:** Marcus doesn't generate root `build.gradle` or `settings.gradle`

**Solution:** These are in the template! AppForge's `compare_folder` only includes **changed** files. If Marcus doesn't modify root gradle files, AppForge uses the template versions automatically.

---

## Recommendation

**Use Option A: `compile_folder()` directly**

### Why:
1. ✅ **Simplest integration** - one function call
2. ✅ **Most robust** - uses AppForge's battle-tested comparison logic
3. ✅ **Least code** - no need to implement anything
4. ✅ **Future-proof** - if AppForge updates their template, it still works

### Implementation in evaluator.py:

```python
from AppForge import AppForge
from pathlib import Path

def evaluate_benchmark(
    task_id: int,
    implementation_dir: Path,
    timeout: int = 1800
) -> dict:
    """Evaluate Marcus implementation against AppForge tests."""

    # Initialize AppForge
    evaluator = AppForge(
        runs=f"marcus_task_{task_id}",
        base_folder=Path.home() / "appforge_benchmarks" / "runs",
        use_docker=True,
        docker_name='zenithfocuslight/appforge:latest',
        docker_port=6080
    )

    try:
        # Compile Marcus's output
        print(f"Compiling Marcus implementation for task {task_id}...")
        compile_error = evaluator.compile_folder(implementation_dir, task_id)

        if compile_error:
            return {
                "task_id": task_id,
                "compile": 0,
                "error": compile_error,
                "pass_rate": 0.0
            }

        # Run tests
        print(f"Running AppForge tests for task {task_id}...")
        result = evaluator.test(task_id)

        # Add task_id to result
        result["task_id"] = task_id
        return result

    finally:
        # Cleanup Docker
        evaluator.clean_up()
```

### That's it! No format conversion needed.

---

## Testing the Integration

1. **Quick test with AppForge alone:**
   ```python
   from AppForge import AppForge
   from pathlib import Path

   evaluator = AppForge("test_run", use_docker=True)

   # Test with a sample Android project
   test_project = Path("/path/to/android/project")
   compile_error = evaluator.compile_folder(test_project, task_id=0)

   if not compile_error:
       result = evaluator.test(0)
       print(result)

   evaluator.clean_up()
   ```

2. **Test with Marcus output:**
   - Run Marcus on a simple task
   - Point AppForge to `implementation/` directory
   - See if it compiles and tests

---

## Summary

**Answer: No complex format conversion needed!**

AppForge already has `compile_folder()` that:
1. Takes a directory path
2. Compares it to their template
3. Extracts differences
4. Compiles the app
5. Returns errors or success

**Just pass Marcus's `implementation/` directory directly to AppForge.**

The only consideration is ensuring Marcus generates valid Android project structure that matches AppForge's template layout (which it should, since it's standard Android Gradle structure).
