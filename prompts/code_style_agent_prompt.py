"""
Marcus Agent Protocol - Pseudocode Example

This is not executable code - it's a conceptual example showing
the agent workflow for documentation purposes.
"""

# type: ignore[no-untyped-def,name-defined]
# mypy: ignore-errors
# This file is pseudocode for documentation purposes only


async def agent_lifecycle() -> None:
    register_agent()  # noqa: F821

    while True:
        task = request_next_task()  # noqa: F821
        if not task:
            continue

        # ALWAYS check dependencies
        for dep_id in task.dependencies:
            context = get_task_context(dep_id)  # noqa: F821
            # Use what you learn

        # Work on task
        await implement_task(task)  # noqa: F821

        # DURING implementation, log choices:
        if choosing_technology():  # noqa: F821
            log_decision(
                "I chose {tech} because {reason}. This affects {impact}."
            )  # noqa: F821

        # Report progress
        for progress in [25, 50, 75, 100]:
            report_task_progress(progress, details)  # noqa: F821

        # CRITICAL: No pause after 100%
        # Loop continues immediately


# Triggers
def should_get_context(task) -> bool:  # type: ignore[no-untyped-def]
    return (
        task.has_dependencies
        or "integrate" in task.description
        or "extend" in task.description
        or "based on" in task.description
    )


def should_log_decision(choice) -> bool:  # type: ignore[no-untyped-def]
    return choice in [
        "database selection",
        "api design pattern",
        "authentication method",
        "naming convention",
        "any architectural choice",
    ]
