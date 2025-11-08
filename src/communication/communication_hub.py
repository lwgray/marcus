"""Multi-channel communication system for Marcus.

This module provides the CommunicationHub class which manages notifications
and messages across different communication channels to keep agents and
managers informed about task assignments, blockers, and project status.

The hub supports asynchronous message delivery through multiple channels
including Slack, email, and kanban board comments.
"""

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.config.settings import Settings
from src.core.models import BlockerReport, Task, TaskAssignment


class CommunicationHub:
    """
    Multi-channel communication system for team coordination.

    Manages notifications and messages across different communication channels
    to keep agents and managers informed about task assignments, blockers,
    and project status.

    Attributes
    ----------
    settings : Settings
        Configuration settings instance
    slack_enabled : bool
        Whether Slack notifications are enabled
    email_enabled : bool
        Whether email notifications are enabled
    kanban_comments_enabled : bool
        Whether kanban board comments are enabled
    message_queue : List[Dict[str, Any]]
        Queue for async message processing
    agent_preferences : Dict[str, Dict[str, Any]]
        Communication preferences by agent ID

    Examples
    --------
    >>> hub = CommunicationHub()
    >>> await hub.notify_task_assignment("agent-001", assignment)
    >>> hub.set_agent_preferences("agent-001", {"daily_plan_channel": "email"})
    """

    def __init__(self) -> None:
        self.settings = Settings()

        # Communication channels (to be initialized based on config)
        self.slack_enabled = self.settings.get("slack_enabled", False)
        self.email_enabled = self.settings.get("email_enabled", False)
        self.kanban_comments_enabled = self.settings.get(
            "kanban_comments_enabled", True
        )

        # Message queue for async processing
        self.message_queue: List[Dict[str, Any]] = []

        # Notification preferences by agent
        self.agent_preferences: Dict[str, Dict[str, Any]] = {}

    async def notify_task_assignment(
        self, agent_id: str, assignment: TaskAssignment
    ) -> None:
        """
        Send task assignment notification through multiple channels.

        Formats and sends assignment notifications via enabled channels
        (kanban comments, Slack, email) in parallel.

        Parameters
        ----------
        agent_id : str
            ID of the agent receiving the assignment
        assignment : TaskAssignment
            The task assignment details

        Notes
        -----
        Notifications are sent asynchronously and exceptions are caught
        to prevent one channel failure from affecting others.
        """
        message = self._format_assignment_message(agent_id, assignment)

        # Send through enabled channels
        tasks = []

        if self.kanban_comments_enabled:
            tasks.append(
                self._send_kanban_comment(assignment.task_id, message["kanban"])
            )

        if self.slack_enabled:
            tasks.append(self._send_slack_message(agent_id, message["slack"]))

        if self.email_enabled:
            tasks.append(
                self._send_email(agent_id, "Task Assignment", message["email"])
            )

        # Execute all notifications in parallel
        await asyncio.gather(*tasks, return_exceptions=True)

    async def notify_blocker(
        self,
        agent_id: str,
        task_id: str,
        blocker_description: str,
        resolution_plan: Dict[str, Any],
    ) -> None:
        """
        Notify relevant parties about a blocker.

        Sends blocker notifications to appropriate recipients based on
        the resolution plan and configured escalation settings.

        Parameters
        ----------
        agent_id : str
            ID of the agent reporting the blocker
        task_id : str
            ID of the blocked task
        blocker_description : str
            Description of what is blocking progress
        resolution_plan : Dict[str, Any]
            Plan containing:
            - resolution_steps: List of steps to resolve
            - impact_assessment: Impact description
            - estimated_hours: Time to resolve
            - required_resources: List of required resources/people
        """
        message = self._format_blocker_message(
            agent_id, task_id, blocker_description, resolution_plan
        )

        # Determine who needs to be notified
        recipients = self._get_blocker_recipients(agent_id, resolution_plan)

        # Send notifications
        tasks = []
        for recipient in recipients:
            if self.slack_enabled:
                tasks.append(self._send_slack_message(recipient, message["slack"]))

        if self.kanban_comments_enabled:
            tasks.append(self._send_kanban_comment(task_id, message["kanban"]))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_clarification(self, agent_id: str, clarification: str) -> None:
        """
        Send clarification response to an agent.

        Sends a clarification message to help an agent understand
        task requirements or resolve questions.

        Parameters
        ----------
        agent_id : str
            ID of the agent to receive clarification
        clarification : str
            The clarification message content
        """
        {
            "type": "clarification",
            "content": clarification,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.slack_enabled:
            await self._send_slack_message(agent_id, clarification)

    async def escalate_blocker(
        self, blocker: BlockerReport, resolution: Dict[str, Any]
    ) -> None:
        """
        Escalate a blocker to management.

        Sends high-priority notifications to configured escalation
        recipients when a blocker requires management intervention.

        Parameters
        ----------
        blocker : BlockerReport
            The blocker report to escalate
        resolution : Dict[str, Any]
            Resolution details containing:
            - required_actions: List of actions needed
            - impact_assessment: Impact description

        Notes
        -----
        Escalation recipients are configured in settings under
        'escalation_recipients' key.
        """
        message = self._format_escalation_message(blocker, resolution)

        # Get escalation recipients
        escalation_list = self.settings.get("escalation_recipients", [])

        tasks = []
        for recipient in escalation_list:
            if self.email_enabled:
                tasks.append(
                    self._send_email(
                        recipient,
                        f"ESCALATION: Blocker on task {blocker.task_id}",
                        message["email"],
                    )
                )

            if self.slack_enabled:
                tasks.append(self._send_slack_message(recipient, message["slack"]))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def notify_task_unblocked(self, task: Task) -> None:
        """
        Notify when a task is unblocked.

        Sends positive notification to assigned agent when their
        blocked task becomes available to work on again.

        Parameters
        ----------
        task : Task
            The task that has been unblocked
        """
        if task.assigned_to:
            message = (
                f"✅ Good news! Task '{task.name}' is now "
                "unblocked and ready to proceed."
            )

            if self.slack_enabled:
                await self._send_slack_message(task.assigned_to, message)

            if self.kanban_comments_enabled:
                await self._send_kanban_comment(
                    task.id,
                    f"🔓 Task unblocked at {datetime.now(timezone.utc).isoformat()}",
                )

    async def send_daily_plan(
        self, agent_id: str, recommendations: List[Dict[str, Any]]
    ) -> None:
        """
        Send personalized daily work plan to agent.

        Sends a formatted daily plan with recommended tasks through
        the agent's preferred communication channel.

        Parameters
        ----------
        agent_id : str
            ID of the agent to receive the plan
        recommendations : List[Dict[str, Any]]
            List of recommended tasks, each containing:
            - task_name: Name of the task
            - priority: Task priority level
            - estimated_hours: Time estimate

        Notes
        -----
        Channel preference is read from agent_preferences. Defaults
        to Slack if no preference is set.
        """
        message = self._format_daily_plan_message(agent_id, recommendations)

        # Send through preferred channel
        pref = self.agent_preferences.get(agent_id, {})
        preferred_channel = pref.get("daily_plan_channel", "slack")

        if preferred_channel == "email" and self.email_enabled:
            await self._send_email(agent_id, "Your Daily Work Plan", message["email"])
        elif self.slack_enabled:
            await self._send_slack_message(agent_id, message["slack"])

    def _format_assignment_message(
        self, agent_id: str, assignment: TaskAssignment
    ) -> Dict[str, str]:
        """
        Format assignment message for different channels.

        Creates channel-specific formatted messages for task assignments.

        Parameters
        ----------
        agent_id : str
            ID of the assigned agent
        assignment : TaskAssignment
            Task assignment details

        Returns
        -------
        Dict[str, str]
            Dictionary with keys:
            - kanban: Markdown formatted for kanban comments
            - slack: Slack markdown formatted message
            - email: HTML formatted email body
        """
        due_date_str = (
            assignment.due_date.strftime("%Y-%m-%d")
            if assignment.due_date
            else "Not set"
        )
        return {
            "kanban": f"""📋 Task assigned to {agent_id}
**Priority:** {assignment.priority.value}
**Estimated Hours:** {assignment.estimated_hours}
**Due Date:** {due_date_str}

**Instructions:**
{assignment.instructions}""",
            "slack": f"""🎯 *New Task Assignment*
*Task:* {assignment.task_name}
*Priority:* {assignment.priority.value}
*Estimated Hours:* {assignment.estimated_hours}

{assignment.instructions}

_Reply with `!help` if you need assistance or `!block` if you encounter issues._""",
            "email": f"""<h2>New Task Assignment</h2>
<p><strong>Task:</strong> {assignment.task_name}</p>
<p><strong>Description:</strong> {assignment.description}</p>
<p><strong>Priority:</strong> {assignment.priority.value}</p>
<p><strong>Estimated Hours:</strong> {assignment.estimated_hours}</p>
<p><strong>Due Date:</strong> {due_date_str}</p>

<h3>Instructions:</h3>
<pre>{assignment.instructions}</pre>

<p>Best regards,<br>AI Project Manager</p>""",
        }

    def _format_blocker_message(
        self,
        agent_id: str,
        task_id: str,
        description: str,
        resolution_plan: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Format blocker message for different channels.

        Creates channel-specific formatted messages for blocker notifications.

        Parameters
        ----------
        agent_id : str
            ID of the agent reporting the blocker
        task_id : str
            ID of the blocked task
        description : str
            Blocker description
        resolution_plan : Dict[str, Any]
            Resolution plan details

        Returns
        -------
        Dict[str, str]
            Dictionary with formatted messages for kanban and slack
        """
        steps = "\n".join(
            [f"• {step}" for step in resolution_plan.get("resolution_steps", [])]
        )

        return {
            "kanban": f"""🚧 Blocker Reported by {agent_id}
**Description:** {description}
**Impact:** {resolution_plan.get('impact_assessment', 'Unknown')}

**Resolution Steps:**
{steps}

**Estimated Resolution Time:** {resolution_plan.get('estimated_hours', 'TBD')} hours""",
            "slack": f"""🚨 *Blocker Alert*
*Task:* {task_id}
*Reporter:* {agent_id}
*Description:* {description}

*Resolution Plan:*
{steps}

_This blocker is being actively addressed._""",
        }

    def _format_escalation_message(
        self, blocker: BlockerReport, resolution: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Format escalation message for management.

        Creates urgent formatted messages for blocker escalations.

        Parameters
        ----------
        blocker : BlockerReport
            The blocker being escalated
        resolution : Dict[str, Any]
            Resolution details with required_actions

        Returns
        -------
        Dict[str, str]
            Dictionary with email and slack formatted messages
        """
        return {
            "email": f"""<h2>Blocker Escalation Required</h2>
<p><strong>Task ID:</strong> {blocker.task_id}</p>
<p><strong>Severity:</strong> {blocker.severity.value}</p>
<p><strong>Reported:</strong> {blocker.reported_at.strftime('%Y-%m-%d %H:%M')}</p>
<p><strong>Description:</strong> {blocker.description}</p>

<h3>Recommended Actions:</h3>
<ul>
{''.join([f'<li>{action}</li>' for action in resolution.get('required_actions', [])])}
</ul>

<p>This blocker requires immediate attention to prevent project delays.</p>""",
            "slack": f"""🚨 *ESCALATION: Blocker Requires Attention*
*Task:* {blocker.task_id}
*Severity:* {blocker.severity.value}
*Description:* {blocker.description}

*Required Actions:*
{chr(10).join(['• ' + action for action in resolution.get('required_actions', [])])}

Please address this blocker immediately.""",
        }

    def _format_daily_plan_message(
        self, agent_id: str, recommendations: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Format daily plan message.

        Creates motivational daily plan messages with task recommendations.

        Parameters
        ----------
        agent_id : str
            ID of the agent
        recommendations : List[Dict[str, Any]]
            List of recommended tasks (up to 5 shown)

        Returns
        -------
        Dict[str, str]
            Dictionary with slack and email formatted messages
        """
        task_list = "\n".join(
            [
                (
                    f"{i+1}. {rec['task_name']} ({rec['priority']}) - "
                    f"{rec['estimated_hours']}h"
                )
                for i, rec in enumerate(recommendations[:5])
            ]
        )

        return {
            "slack": f"""☀️ *Good morning, {agent_id}!*

*Your recommended tasks for today:*
{task_list}

*Tips for today:*
• Focus on high-priority items first
• Reach out if you encounter any blockers
• Update task progress regularly

Have a productive day! 🚀""",
            "email": (
                f"""<h2>Your Daily Work Plan</h2>
<p>Good morning, {agent_id}!</p>

<h3>Recommended Tasks:</h3>
<ol>
{''.join([
    f'<li>{rec["task_name"]} (Priority: {rec["priority"]}) - '
    f'{rec["estimated_hours"]} hours</li>'
    for rec in recommendations[:5]
])}
</ol>

<p>Remember to update your progress throughout the day """
                "and reach out if you need any assistance.</p>\n\n"
                "<p>Best regards,<br>AI Project Manager</p>"
            ),
        }

    def _get_blocker_recipients(
        self, reporter_id: str, resolution_plan: Dict[str, Any]
    ) -> List[str]:
        """
        Determine who should be notified about a blocker.

        Builds recipient list including reporter, team lead, and any
        specific resources mentioned in the resolution plan.

        Parameters
        ----------
        reporter_id : str
            ID of the blocker reporter
        resolution_plan : Dict[str, Any]
            Plan potentially containing required_resources

        Returns
        -------
        List[str]
            Unique list of recipient IDs
        """
        recipients = [reporter_id]

        # Add team lead
        team_lead = self.settings.get("team_lead_id")
        if team_lead:
            recipients.append(team_lead)

        # Add specific resources mentioned in resolution plan
        required_resources = resolution_plan.get("required_resources", [])
        for resource in required_resources:
            if "@" in resource:  # Assuming email/id format
                recipients.append(resource)

        return list(set(recipients))  # Remove duplicates

    async def _send_kanban_comment(self, task_id: str, comment: str) -> None:
        """
        Send comment to kanban board.

        Posts a comment to the specified task on the kanban board.

        Parameters
        ----------
        task_id : str
            ID of the task to comment on
        comment : str
            Comment text to post

        Notes
        -----
        Currently simulates the operation. In production, this would
        integrate with the kanban client.
        """
        # This would integrate with the kanban client
        # For now, we'll simulate it
        print(f"[KANBAN] Task {task_id}: {comment}", file=sys.stderr)

    async def _send_slack_message(self, recipient: str, message: str) -> None:
        """
        Send Slack message.

        Sends a direct message to the specified recipient via Slack.

        Parameters
        ----------
        recipient : str
            Slack user ID or channel
        message : str
            Message content with Slack markdown

        Notes
        -----
        Currently simulates the operation. In production, this would
        integrate with Slack SDK.
        """
        # This would integrate with Slack SDK
        # For now, we'll simulate it
        print(f"[SLACK] To {recipient}: {message}", file=sys.stderr)

    async def _send_email(self, recipient: str, subject: str, body: str) -> None:
        """
        Send email notification.

        Sends an HTML formatted email to the specified recipient.

        Parameters
        ----------
        recipient : str
            Email address of recipient
        subject : str
            Email subject line
        body : str
            HTML formatted email body

        Notes
        -----
        Currently simulates the operation. In production, this would
        integrate with an email service provider.
        """
        # This would integrate with email service
        # For now, we'll simulate it
        print(f"[EMAIL] To {recipient} - Subject: {subject}", file=sys.stderr)
        print(f"Body: {body[:200]}...", file=sys.stderr)

    def set_agent_preferences(self, agent_id: str, preferences: Dict[str, Any]) -> None:
        """
        Set communication preferences for an agent.

        Stores agent-specific communication preferences to customize
        how they receive notifications.

        Parameters
        ----------
        agent_id : str
            ID of the agent
        preferences : Dict[str, Any]
            Preference dictionary, may contain:
            - daily_plan_channel: "email" or "slack"
            - notification_hours: Active hours for notifications
            - quiet_mode: Boolean for reduced notifications

        Examples
        --------
        >>> hub.set_agent_preferences("agent-001", {
        ...     "daily_plan_channel": "email",
        ...     "quiet_mode": False
        ... })
        """
        self.agent_preferences[agent_id] = preferences
