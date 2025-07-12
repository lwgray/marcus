MARCUS AGENT TRIGGERS:

IF task.dependencies → get_task_context(each)
IF "integrate/extend/based on" → get_task_context(relevant_tasks)
IF choosing_database → log_decision("chose X because Y. affects Z")
IF choosing_api_pattern → log_decision("chose X because Y. affects Z")
IF choosing_auth_method → log_decision("chose X because Y. affects Z")
IF setting_any_pattern → log_decision("chose X because Y. affects Z")
IF progress = 100% → request_next_task() // NO WAIT

ALWAYS:
- Check dependencies before starting
- Log decisions when making them
- Request next task immediately after completion

NEVER:
- Wait for permission
- Skip dependency checks
- Hide architectural choices
