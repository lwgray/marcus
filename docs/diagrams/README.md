# Task Description Flow Documentation

Understanding how your project description becomes agent instructions.

## Documents in This Directory

### 1. [task-description-flow.md](task-description-flow.md)
**Complete flow from create_project to agent instructions**

Shows:
- Every step from MCP tool to Planka
- Where templates are applied (line numbers)
- What gets lost vs preserved
- The "smoking gun" - template replacement at line 1358-1650

Use when:
- Debugging why descriptions seem generic
- Understanding the full pipeline
- Identifying where changes need to be made

### 2. [how-context-preserved.md](how-context-preserved.md)
**HOW agents still build the right thing despite templates**

Shows:
- Task names preserve feature context
- Specific requirements appended to descriptions
- Business objectives injected from PRD analysis
- All tasks visible to agents (project context)

Use when:
- Understanding "wait, it works though?"
- Explaining to others how context flows
- Verifying what AI actually sees

---

## Quick Reference

### The Problem
User input: "Build a todo app with auth, CRUD, and filtering"

Task description becomes:
```
"Create detailed UI/UX design for frontend application. Include component
hierarchy, design system, responsive layouts..."
```

Looks generic!

### The Solution
But the FULL context includes:

1. **Task name:** "Design User Authentication"
2. **Description:** "...Focus on achieving: Increase user engagement through an intuitive and secure todo app. Specific requirement: Implement user registration and login functionality using JWT..."
3. **Labels:** ["feature:user-auth"]
4. **All tasks:** Agent sees all 11 tasks with specific names

AI combines all of this → generates correct instructions

---

## Key Code Locations

| What | File | Line | Purpose |
|------|------|------|---------|
| Template generation | `src/ai/advanced/prd/advanced_parser.py` | 1358-1650 | Where generic templates are created |
| Requirement appending | `src/ai/advanced/prd/advanced_parser.py` | 1467-1472 | Where specific requirements are added |
| Project context | `src/ai/advanced/prd/advanced_parser.py` | 1235-1330 | Extracts objectives, constraints |
| Instruction generation | `src/integrations/ai_analysis_engine.py` | 427-495 | What AI sees when generating instructions |
| Task assignment | `src/marcus_mcp/tools/task.py` | 215-495 | How agents get tasks and context |

---

## Testing Tools

### Preview (Before Creation)
```bash
python scripts/preview_project_plan.py "Your description" "project_name"
# Shows: What will be created
# Output: data/diagnostics/project_preview.md
```

### Diagnose (After Creation)
```bash
# Edit line 39 first to set project name
python scripts/diagnose_task_descriptions.py
# Shows: What was created, instruction flow
# Output: data/diagnostics/description_analysis.md
```

### Show AI Input
```bash
python scripts/show_ai_input.py
# Shows: Exactly what AI sees
# Output: Console only
```

---

## Common Questions

### Q: Are descriptions lost?
**A:** No! Templates provide structure, but they also include:
- Specific requirements appended
- Business objectives injected
- Project type from analysis

### Q: How do agents know what to build?
**A:** From FOUR sources:
1. Task name (feature-specific)
2. Description (template + requirements)
3. Labels (domain tags)
4. All tasks (project context)

### Q: Should I improve the templates?
**A:** Maybe! Options:
1. Use AI to generate descriptions (better)
2. Use PRD analysis directly (good)
3. Keep templates but enhance them (okay)

See [task-description-flow.md](task-description-flow.md) for solutions.

---

## Workflow

1. **Before creating project:**
   ```bash
   python scripts/preview_project_plan.py "description" "name"
   ```
   Review: Do task names and descriptions make sense?

2. **Create project:**
   ```python
   mcp__marcus__create_project(description="...", project_name="...")
   ```

3. **After creation:**
   ```bash
   python scripts/diagnose_task_descriptions.py
   ```
   Check: Are there description mismatches?

4. **If issues found:**
   - Read [how-context-preserved.md](how-context-preserved.md)
   - Check if context is actually missing
   - Review [task-description-flow.md](task-description-flow.md) for fixes

---

## Mermaid Diagrams

Both documents include detailed Mermaid diagrams:

**task-description-flow.md:**
- Shows full pipeline with problem areas highlighted in red
- Traces from user input → templating → Planka → agent

**how-context-preserved.md:**
- Shows how context flows through multiple channels
- Explains why it works despite templates

---

## For Developers

### Want to improve descriptions?

1. **Quick fix:** Enhance templates with more variables
   - File: `src/ai/advanced/prd/advanced_parser.py`
   - Functions: `_generate_design_task`, `_generate_implementation_task`, etc
   - Add more context variables to templates

2. **Better fix:** Use AI to generate descriptions
   - Replace template functions with AI calls
   - Pass original PRD content to AI
   - Generate feature-specific descriptions

3. **Best fix:** Store original PRD in task.description
   - Use templates for structure only
   - Keep full context in description
   - Let AI extract what it needs

### Want to add more context?

Modify `build_tiered_instructions` in `src/marcus_mcp/tools/task.py:25-162`
- Adds layers on top of base instructions
- Can inject more project context
- Good place to add related task info

---

## Summary

**Your description IS preserved**, just in multiple pieces:

```
Original: "Build a todo app with auth, CRUD, and filtering"

Becomes:
├── Task names: "Design User Authentication", "CRUD Operations for Todos"
├── Description: Template + "Specific requirement: implement auth with JWT"
├── Objectives: "Increase engagement through intuitive todo app"
├── Labels: "feature:user-auth", "feature:crud-operations"
└── Context: All 11 tasks visible to agents

Agent receives → AI combines → Generates correct instructions
```

The system works, it's just more distributed than you might expect!
