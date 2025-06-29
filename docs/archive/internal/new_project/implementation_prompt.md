# Implementation Prompt for Marcus Hybrid Approach

Use this prompt when you're ready to start implementing the hybrid intelligent coordination system.

---

## Implementation Prompt for Marcus Hybrid Approach

**Context**: I want to implement the hybrid intelligent project coordination system for Marcus as documented in the `/Users/lwgray/dev/marcus/docs/` folder, starting with Phase 1. Marcus currently assigns tasks randomly without understanding dependencies (like assigning "Deploy to production" before anything is built).

**Current State**:
- Marcus MCP server is at `/Users/lwgray/dev/marcus/marcus_mcp_server.py`
- Using Planka/GitHub/Linear for kanban boards
- SimpleMCPKanbanClient connects to boards
- Basic task assignment works but lacks intelligence
- Config is in `config_marcus.json`

**Request**: Please guide me through implementing Phase 1 (Foundation) of the hybrid approach, specifically:

1. **Context Detection System** - Detect board state and recommend appropriate mode
2. **Basic Creator Mode** - Generate properly ordered tasks from templates
3. **Basic Adaptive Mode** - Assign tasks respecting dependencies
4. **Mode Switching** - Allow users to switch between modes

**Implementation Needs**:
- Create the new directory structure
- Implement the board analyzer
- Add basic dependency checking
- Update `find_optimal_task_for_agent` to use the new logic
- Add new MCP tools for mode switching
- Ensure backwards compatibility

**Success Criteria**:
- Marcus never assigns deployment before development
- Marcus can detect if a board needs structure
- Marcus can generate a basic project from a template
- Users can explicitly switch modes

Please start with the directory structure and the first component (board analyzer), then guide me through each piece step by step.

---

## Additional Context You Can Add

When using this prompt, you may want to add:

1. **Specific Priority**: "Focus on preventing illogical task assignments first"
2. **Time Constraint**: "I have 2 hours today, what can we accomplish?"
3. **Testing Preference**: "I want to use TDD for this implementation"
4. **Integration Focus**: "Start with Planka integration only"

## Expected Response

The assistant should:
1. Review the documentation structure
2. Create a step-by-step implementation plan
3. Start with creating directories and files
4. Implement the board analyzer first
5. Add tests for each component
6. Guide you through integration with existing code

## Follow-up Prompts

After initial implementation:
- "Now let's implement the basic Creator Mode with templates"
- "Show me how to add dependency checking to the task selection"
- "Let's add the mode switching MCP tools"
- "How do we test that deployment is never assigned first?"

---

This prompt ensures you get structured, systematic help implementing the solution to Marcus's intelligence problem.