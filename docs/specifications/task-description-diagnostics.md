# Task Description Diagnostic Tools

Two tools to help you understand how task descriptions flow through Marcus.

## 1. Preview Project Plan (BEFORE Planka)

**Purpose:** See what Marcus will create BEFORE committing to Planka.

**Script:** `scripts/preview_project_plan.py`

**Usage:**
```bash
python scripts/preview_project_plan.py "<description>" "<project_name>"

# Example
python scripts/preview_project_plan.py "Build a todo app with auth" "MyTodoApp"
```

**Output:**
- `data/diagnostics/project_preview.md` - Human-readable markdown
- `data/diagnostics/project_preview.json` - Machine-readable JSON

**What You See:**
- Original description
- All tasks Marcus plans to create
- Task descriptions, priorities, dependencies
- Estimated hours and resource requirements
- Dependency analysis
- Tasks ready to start immediately

**When to Use:**
- Before creating a new project
- To validate your description is clear
- To check if tasks match expectations
- To understand task breakdown logic

---

## 2. Diagnose Task Descriptions (AFTER Planka)

**Purpose:** Analyze tasks already on Planka board and trace how descriptions transform into agent instructions.

**Script:** `scripts/diagnose_task_descriptions.py`

**Usage:**
```bash
python scripts/diagnose_task_descriptions.py
```

**Note:** Edit line 39 to change the project name:
```python
kanban_config = {"project_name": "your_project_name"}
```

**Output:**
- `data/diagnostics/description_analysis.md` - Full analysis report
- `data/diagnostics/description_analysis.json` - Raw data

**What You See:**
- Task names vs descriptions (mismatch detection)
- Original descriptions from Planka
- Subtasks (if decomposed)
- Generated agent instructions
- Relevance scoring

**When to Use:**
- After project creation
- When agents seem confused about tasks
- To debug description → instruction flow
- To identify generic/template descriptions

---

## Workflow

### Recommended Process:

1. **Preview First**
   ```bash
   python scripts/preview_project_plan.py "Your description" "project_name"
   ```
   Review `data/diagnostics/project_preview.md`

2. **Refine if Needed**
   - If tasks don't match expectations, refine description
   - Repeat preview until satisfied

3. **Create Project**
   ```python
   mcp__marcus__create_project(
       description="Your description",
       project_name="project_name",
       options={"mode": "new_project"}
   )
   ```

4. **Diagnose After Creation**
   ```bash
   # Edit script to set project name
   python scripts/diagnose_task_descriptions.py
   ```
   Review `data/diagnostics/description_analysis.md`

5. **Check for Issues**
   - Look for ❌ mismatch flags
   - Review agent instructions
   - Verify subtask breakdowns

---

## Common Issues Detected

### Issue 1: Generic Descriptions
**Symptom:** Task name says "Implement Login" but description is generic "Create API endpoints"

**Solution:** Marcus templates are too generic - add more specificity to original project description

### Issue 2: Missing Context
**Symptom:** Agent instructions don't mention key requirements

**Solution:** Task description lost details - check subtask decomposition or enhance main description

### Issue 3: Name/Description Mismatch
**Symptom:** ❌ flag in analysis report

**Solution:** Task naming doesn't match content - may confuse agents

---

## Key Differences

| Feature | Preview (Before) | Diagnose (After) |
|---------|------------------|------------------|
| **When** | Before Planka creation | After tasks on board |
| **Purpose** | Validate plan | Debug issues |
| **Input** | Description text | Planka board data |
| **Shows** | What WILL be created | What WAS created |
| **Agent Instructions** | Not generated yet | Fully generated |
| **Subtasks** | Not created yet | Shows decomposition |
| **Edit Script** | No | Yes (line 39) |

---

## Files Generated

### Preview Tool
- `data/diagnostics/project_preview.md` - Markdown report
- `data/diagnostics/project_preview.json` - JSON data

### Diagnosis Tool
- `data/diagnostics/description_analysis.md` - Full analysis
- `data/diagnostics/description_analysis.json` - Raw data

---

## Tips

1. **Always preview first** - Save time by catching issues before creation

2. **Compare preview vs actual** - Run both tools to see what changed

3. **Check confidence scores** - Preview shows AI confidence (0.0-1.0)

4. **Review dependencies** - Both tools show dependency graphs

5. **Use for debugging** - When agents struggle, run diagnosis to see what they received

---

## Configuration

### Preview Tool
No configuration needed - works standalone

### Diagnosis Tool
Edit `scripts/diagnose_task_descriptions.py` line 39:
```python
kanban_config = {"project_name": "your_project_here"}
```

---

## Troubleshooting

### Preview fails with "No module"
```bash
# Ensure you're in the marcus directory
cd /path/to/marcus
python scripts/preview_project_plan.py ...
```

### Diagnosis shows empty tasks
- Check project name in script (line 39)
- Verify Planka connection
- Ensure tasks exist on board

### Instructions show [Error: ...]
- Check WorkerStatus parameters in script
- Verify AI engine is initialized
- See error message for details
