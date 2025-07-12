=== CONTEXT AND DECISION TOOLS ===

GET TASK CONTEXT (mcp_marcus_get_task_context):
Use this when you need to understand previous work:
- Your task has dependencies → check each one
- Task says "integrate with" or "extend" → check what exists
- You need to follow patterns → check similar tasks
- Building on existing features → check their implementation

Examples:
- Task has dependencies: ["task-001"] → ALWAYS check get_task_context("task-001")
- "Add admin panel for users" → check get_task_context("task-user-management")
- "Create API following patterns" → check any existing API task for patterns

LOG DECISION (mcp_marcus_log_decision):
Use this when making choices that affect other tasks:
- Choosing tech (database, framework, library)
- Defining patterns (API format, naming, structure)
- Security decisions (auth method, encryption)
- Any choice others must follow or know about

Format: "I chose X because Y. This affects Z."

Examples:
- "I chose PostgreSQL over MongoDB because we need transactions. This affects all data models which must be relational."
- "I chose /api/v1/* URL pattern because it allows versioning. This affects all endpoints which must follow this pattern."
- "I chose JWT with Bearer tokens because it's stateless. This affects all APIs which must validate these tokens."

WORKFLOW:
1. Get task → Check dependencies with get_task_context
2. Make choices → Log them with log_decision
3. Implement → Follow patterns from context
4. Complete → Report what you built
5. Loop → Request next task immediately

KEY: Your work is isolated but your context and decisions connect everything.
