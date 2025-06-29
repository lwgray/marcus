# Documentation System Prompt for AI Agents

Add this to your agent's system prompt or CLAUDE.md file:

## System Prompt Addition

```
# Documentation Creation and Placement Rules

When creating or updating documentation for this project, follow these rules:

## Documentation Structure
The documentation is organized by audience:
- `/docs/user-guide/` - For end users of the system
- `/docs/developer-guide/` - For developers and contributors  
- `/docs/operations-guide/` - For deployment and operations
- `/docs/archive/` - For internal planning and historical docs

## Placement Rules

1. **Determine the primary audience first:**
   - If explaining how to USE a feature → `/docs/user-guide/`
   - If explaining how to BUILD/MODIFY code → `/docs/developer-guide/`
   - If explaining how to DEPLOY/OPERATE → `/docs/operations-guide/`
   - If internal notes/planning → `/docs/archive/`

2. **Choose the appropriate subdirectory:**
   - Step-by-step instructions → `how-to/`
   - Conceptual explanations → `concepts/`
   - Configuration/settings → `reference/`
   - API/Technical details → put in developer-guide root or `sphinx/source/`

3. **File naming:**
   - Use kebab-case: `my-feature-guide.md`
   - Be descriptive: `configure-github-integration.md` not `github.md`
   - Include the type: `how-to-bulk-import-tasks.md`

4. **Before creating new documentation:**
   - Check if similar documentation already exists
   - Update existing docs rather than creating duplicates
   - Each directory has a README.md that explains what belongs there

5. **Content guidelines:**
   - User docs: Simple language, lots of examples, avoid jargon
   - Developer docs: Technical accuracy, code examples, architecture details
   - Operations docs: Prerequisites, environment variables, troubleshooting

## Examples of correct placement:
- "How to create tasks" → `/docs/user-guide/how-to/create-tasks.md`
- "Task API reference" → `/docs/developer-guide/task-api.md`
- "Deploy on AWS" → `/docs/operations-guide/setup/deploy-aws.md`
- "Architecture overview" → `/docs/developer-guide/sphinx/source/developer/architecture.md`
- "Meeting notes" → `/docs/archive/planning/2024-01-meeting-notes.md`

## When in doubt:
1. Check `/docs/README.md` for the complete structure
2. Look at similar existing documentation
3. Consider who will be reading this documentation
4. Place it where that audience would naturally look for it
```

## For CLAUDE.md or .claude_instructions

```markdown
# Documentation Standards

Always follow the project's documentation organization:
- User documentation goes in `/docs/user-guide/`
- Developer documentation goes in `/docs/developer-guide/`  
- Deployment/operations docs go in `/docs/operations-guide/`
- Internal documents go in `/docs/archive/`

Before creating new documentation:
1. Check if it already exists
2. Determine the primary audience
3. Place it in the correct directory
4. Use descriptive kebab-case filenames
5. Link to related documentation

Each documentation directory has a README.md explaining what belongs there.
Follow the existing patterns and style in each section.
```

## Minimal Version for Space-Constrained Prompts

```
When creating documentation:
- User guides → /docs/user-guide/
- Developer docs → /docs/developer-guide/
- Operations → /docs/operations-guide/
- How-tos → add how-to/ subdirectory
- Check existing docs first
- Follow naming patterns in each directory
```