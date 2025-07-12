Marcus Agent Checklist:

□ START: register_agent (once only)

□ EACH TASK:
  ✓ request_next_task
  ✓ Has dependencies? → get_task_context(each)
  ✓ Do work
  ✓ Made a choice? → log_decision("chose X because Y. affects Z")
  ✓ report_task_progress: 25%, 50%, 75%, 100%
  ✓ At 100% → request_next_task IMMEDIATELY

□ GET CONTEXT WHEN:
  - task.dependencies exists
  - task says "integrate/extend/based on"

□ LOG DECISION WHEN:
  - choosing database/framework/library
  - defining API pattern/format
  - setting convention others follow

□ NEVER:
  - wait after completing task
  - skip checking dependencies
  - make choices without logging why
