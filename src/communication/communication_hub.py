import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from src.core.models import TaskAssignment, Task, BlockerReport
from src.config.settings import Settings


class CommunicationHub:
    """Multi-channel communication system for team coordination"""
    
    def __init__(self):
        self.settings = Settings()
        
        # Communication channels (to be initialized based on config)
        self.slack_enabled = self.settings.get("slack_enabled", False)
        self.email_enabled = self.settings.get("email_enabled", False)
        self.kanban_comments_enabled = self.settings.get("kanban_comments_enabled", True)
        
        # Message queue for async processing
        self.message_queue: List[Dict[str, Any]] = []
        
        # Notification preferences by agent
        self.agent_preferences: Dict[str, Dict[str, Any]] = {}
    
    async def notify_task_assignment(
        self,
        agent_id: str,
        assignment: TaskAssignment
    ):
        """Send task assignment notification through multiple channels"""
        message = self._format_assignment_message(agent_id, assignment)
        
        # Send through enabled channels
        tasks = []
        
        if self.kanban_comments_enabled:
            tasks.append(self._send_kanban_comment(assignment.task_id, message["kanban"]))
        
        if self.slack_enabled:
            tasks.append(self._send_slack_message(agent_id, message["slack"]))
        
        if self.email_enabled:
            tasks.append(self._send_email(agent_id, "Task Assignment", message["email"]))
        
        # Execute all notifications in parallel
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def notify_blocker(
        self,
        agent_id: str,
        task_id: str,
        blocker_description: str,
        resolution_plan: Dict[str, Any]
    ):
        """Notify relevant parties about a blocker"""
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
    
    async def send_clarification(
        self,
        agent_id: str,
        clarification: str
    ):
        """Send clarification response to an agent"""
        message = {
            "type": "clarification",
            "content": clarification,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.slack_enabled:
            await self._send_slack_message(agent_id, clarification)
    
    async def escalate_blocker(
        self,
        blocker: BlockerReport,
        resolution: Dict[str, Any]
    ):
        """Escalate a blocker to management"""
        message = self._format_escalation_message(blocker, resolution)
        
        # Get escalation recipients
        escalation_list = self.settings.get("escalation_recipients", [])
        
        tasks = []
        for recipient in escalation_list:
            if self.email_enabled:
                tasks.append(self._send_email(
                    recipient,
                    f"ESCALATION: Blocker on task {blocker.task_id}",
                    message["email"]
                ))
            
            if self.slack_enabled:
                tasks.append(self._send_slack_message(recipient, message["slack"]))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def notify_task_unblocked(self, task: Task):
        """Notify when a task is unblocked"""
        if task.assigned_to:
            message = f"✅ Good news! Task '{task.name}' is now unblocked and ready to proceed."
            
            if self.slack_enabled:
                await self._send_slack_message(task.assigned_to, message)
            
            if self.kanban_comments_enabled:
                await self._send_kanban_comment(
                    task.id,
                    f"🔓 Task unblocked at {datetime.now().isoformat()}"
                )
    
    async def send_daily_plan(
        self,
        agent_id: str,
        recommendations: List[Dict[str, Any]]
    ):
        """Send personalized daily work plan to agent"""
        message = self._format_daily_plan_message(agent_id, recommendations)
        
        # Send through preferred channel
        pref = self.agent_preferences.get(agent_id, {})
        preferred_channel = pref.get("daily_plan_channel", "slack")
        
        if preferred_channel == "email" and self.email_enabled:
            await self._send_email(agent_id, "Your Daily Work Plan", message["email"])
        elif self.slack_enabled:
            await self._send_slack_message(agent_id, message["slack"])
    
    def _format_assignment_message(
        self,
        agent_id: str,
        assignment: TaskAssignment
    ) -> Dict[str, str]:
        """Format assignment message for different channels"""
        return {
            "kanban": f"""📋 Task assigned to {agent_id}
**Priority:** {assignment.priority.value}
**Estimated Hours:** {assignment.estimated_hours}
**Due Date:** {assignment.due_date.strftime('%Y-%m-%d') if assignment.due_date else 'Not set'}

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
<p><strong>Due Date:</strong> {assignment.due_date.strftime('%Y-%m-%d') if assignment.due_date else 'Not set'}</p>

<h3>Instructions:</h3>
<pre>{assignment.instructions}</pre>

<p>Best regards,<br>AI Project Manager</p>"""
        }
    
    def _format_blocker_message(
        self,
        agent_id: str,
        task_id: str,
        description: str,
        resolution_plan: Dict[str, Any]
    ) -> Dict[str, str]:
        """Format blocker message for different channels"""
        steps = "\n".join([f"• {step}" for step in resolution_plan.get("resolution_steps", [])])
        
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

_This blocker is being actively addressed._"""
        }
    
    def _format_escalation_message(
        self,
        blocker: BlockerReport,
        resolution: Dict[str, Any]
    ) -> Dict[str, str]:
        """Format escalation message"""
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

Please address this blocker immediately."""
        }
    
    def _format_daily_plan_message(
        self,
        agent_id: str,
        recommendations: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Format daily plan message"""
        task_list = "\n".join([
            f"{i+1}. {rec['task_name']} ({rec['priority']}) - {rec['estimated_hours']}h"
            for i, rec in enumerate(recommendations[:5])
        ])
        
        return {
            "slack": f"""☀️ *Good morning, {agent_id}!*

*Your recommended tasks for today:*
{task_list}

*Tips for today:*
• Focus on high-priority items first
• Reach out if you encounter any blockers
• Update task progress regularly

Have a productive day! 🚀""",
            
            "email": f"""<h2>Your Daily Work Plan</h2>
<p>Good morning, {agent_id}!</p>

<h3>Recommended Tasks:</h3>
<ol>
{''.join([f'<li>{rec["task_name"]} (Priority: {rec["priority"]}) - {rec["estimated_hours"]} hours</li>' for rec in recommendations[:5]])}
</ol>

<p>Remember to update your progress throughout the day and reach out if you need any assistance.</p>

<p>Best regards,<br>AI Project Manager</p>"""
        }
    
    def _get_blocker_recipients(
        self,
        reporter_id: str,
        resolution_plan: Dict[str, Any]
    ) -> List[str]:
        """Determine who should be notified about a blocker"""
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
    
    async def _send_kanban_comment(self, task_id: str, comment: str):
        """Send comment to kanban board"""
        # This would integrate with the kanban client
        # For now, we'll simulate it
        print(f"[KANBAN] Task {task_id}: {comment}")
    
    async def _send_slack_message(self, recipient: str, message: str):
        """Send Slack message"""
        # This would integrate with Slack SDK
        # For now, we'll simulate it
        print(f"[SLACK] To {recipient}: {message}")
    
    async def _send_email(self, recipient: str, subject: str, body: str):
        """Send email"""
        # This would integrate with email service
        # For now, we'll simulate it
        print(f"[EMAIL] To {recipient} - Subject: {subject}")
        print(f"Body: {body[:200]}...")
    
    def set_agent_preferences(
        self,
        agent_id: str,
        preferences: Dict[str, Any]
    ):
        """Set communication preferences for an agent"""
        self.agent_preferences[agent_id] = preferences