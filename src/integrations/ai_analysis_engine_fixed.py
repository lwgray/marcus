"""
AI-powered analysis and decision engine for Marcus.

This module provides intelligent task assignment, blocker resolution, and project
risk analysis using Claude API. It includes comprehensive fallback mechanisms
for when the AI service is unavailable.

The engine helps with:
- Optimal task-to-agent matching based on skills and capacity
- Generating detailed task instructions
- Analyzing and resolving blockers
- Identifying project risks and mitigation strategies

Examples
--------
>>> engine = AIAnalysisEngine()
>>> await engine.initialize()
>>> task = await engine.match_task_to_agent(tasks, agent, project_state)
>>> instructions = await engine.generate_task_instructions(task, agent)
"""

import json
import os
import sys
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta

import anthropic

from src.core.models import (
    Task, WorkerStatus, ProjectState, 
    RiskLevel, Priority, BlockerReport, ProjectRisk
)


class AIAnalysisEngine:
    """
    AI-powered analysis and decision engine using Claude API.
    
    This class provides intelligent analysis for project management decisions,
    including task assignment optimization, blocker resolution, and risk analysis.
    It gracefully falls back to rule-based approaches when AI is unavailable.
    
    Attributes
    ----------
    client : Optional[anthropic.Anthropic]
        Anthropic API client, None if unavailable
    model : str
        Claude model to use for analysis
    prompts : Dict[str, str]
        Template prompts for different analysis types
    
    Examples
    --------
    >>> engine = AIAnalysisEngine()
    >>> await engine.initialize()
    >>> # Engine is ready for analysis tasks
    
    Notes
    -----
    Requires ANTHROPIC_API_KEY environment variable for AI features.
    Works in fallback mode without the API key.
    """
    
    def __init__(self) -> None:
        """
        Initialize the AI Analysis Engine.
        
        Attempts to set up the Anthropic client with various compatibility
        approaches for different library versions.
        """
        # Initialize Anthropic client with better error handling
        self.client: Optional[anthropic.Anthropic] = None
        try:
            # Get API key from config first, fall back to environment
            from src.config.config_loader import get_config
            config = get_config()
            api_key = config.get('ai.anthropic_api_key') or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                print("⚠️  Anthropic API key not found - AI features will use fallback mode", file=sys.stderr)
                self.client = None
            else:
                # Try different initialization approaches based on version
                try:
                    # First try simple initialization
                    self.client = anthropic.Anthropic(api_key=api_key)
                    print("✅ Anthropic client initialized successfully", file=sys.stderr)
                except TypeError as te:
                    # If we get a TypeError about proxies, try with explicit None
                    if 'proxies' in str(te):
                        print("⚠️  Retrying Anthropic init with proxies=None", file=sys.stderr)
                        self.client = anthropic.Anthropic(api_key=api_key, proxies=None)
                        print("✅ Anthropic client initialized with proxies=None", file=sys.stderr)
                    else:
                        raise te
                
        except Exception as e:
            print(f"⚠️  Failed to initialize Anthropic client: {e}", file=sys.stderr)
            print("   AI features will use fallback responses", file=sys.stderr)
            self.client = None
        
        self.model: str = config.get('ai.model', 'claude-3-5-sonnet-20241022') if 'config' in locals() else "claude-3-5-sonnet-20241022"  # Using Sonnet 3.5 for speed/cost balance
        
        # Analysis prompts
        self.prompts: Dict[str, str] = {
            "task_assignment": """You are an AI Project Manager analyzing task assignments.
            
Given:
- Available tasks: {tasks}
- Agent profile: {agent}
- Project state: {project_state}

Analyze and recommend the SINGLE BEST task for this agent considering:
1. Agent's skills match task requirements
2. Agent's current capacity and workload
3. Task priority and dependencies
4. Project timeline and critical path

Return JSON:
{{
    "recommended_task_id": "id",
    "confidence_score": 0.0-1.0,
    "reasoning": "explanation"
}}""",

            "task_instructions": """You are generating detailed task instructions for a developer.

Task: {task}
Assigned to: {agent}

Generate clear, actionable instructions that:
1. Define the task objective
2. List specific steps to complete it
3. Include acceptance criteria
4. Note any dependencies or prerequisites
5. Suggest tools/resources to use

Format as structured text the developer can follow.""",

            "blocker_analysis": """Analyze this blocker and suggest resolution:

Task ID: {task_id}
Blocker: {description}
Severity: {severity}
{agent_context}
{task_context}

Consider the agent's skills, experience level, and current workload when providing suggestions.
Tailor resolution steps to their capabilities and provide learning opportunities if appropriate.

Provide JSON response:
{{
    "root_cause": "analysis",
    "impact_assessment": "description", 
    "resolution_steps": ["step1 tailored to agent skills", "step2"],
    "required_resources": ["resource1"],
    "estimated_hours": number,
    "escalation_needed": boolean,
    "prevention_measures": ["measure1"],
    "learning_opportunities": ["skill gaps identified"],
    "recommended_collaborators": ["team members with needed skills"],
    "skill_match_confidence": "high/medium/low"
}}""",

            "project_risk": """Analyze project risks based on current state:

Project State: {project_state}
Recent Blockers: {recent_blockers}
Team Status: {team_status}

Identify risks and provide JSON:
{{
    "risks": [
        {{
            "description": "risk description",
            "likelihood": "low|medium|high",
            "impact": "low|medium|high",
            "mitigation": "suggested action"
        }}
    ],
    "overall_health": "healthy|at_risk|critical",
    "recommended_actions": ["action1", "action2"]
}}"""
        }
    
    async def initialize(self) -> None:
        """
        Initialize the AI engine and test connectivity.
        
        Verifies the Anthropic client can communicate with the API by
        sending a test message. Disables the client if the test fails.
        
        Examples
        --------
        >>> engine = AIAnalysisEngine()
        >>> await engine.initialize()
        ✅ AI Engine connection verified
        """
        if not self.client:
            print("⚠️  AI Engine running in fallback mode (no Anthropic client)", file=sys.stderr)
            return
        
        # Test connection
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            print("✅ AI Engine connection verified", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  AI Engine test failed: {e}", file=sys.stderr)
            print("   Will use fallback responses", file=sys.stderr)
            self.client = None  # Disable client if test fails
    
    async def match_task_to_agent(
        self, 
        available_tasks: List[Task], 
        agent: WorkerStatus,
        project_state: ProjectState
    ) -> Optional[Task]:
        """
        Find the optimal task for an agent using AI analysis.
        
        Parameters
        ----------
        available_tasks : List[Task]
            List of unassigned tasks to choose from
        agent : WorkerStatus
            Agent profile including skills and capacity
        project_state : ProjectState
            Current state of the project
        
        Returns
        -------
        Optional[Task]
            The best matching task, or None if no suitable task found
        
        Examples
        --------
        >>> task = await engine.match_task_to_agent(
        ...     tasks, agent, ProjectState.HEALTHY
        ... )
        >>> print(f"Assigned: {task.name} to {agent.name}")
        
        Notes
        -----
        Falls back to skill-based matching if AI is unavailable.
        Considers up to 10 tasks to avoid context limits.
        """
        if not available_tasks:
            return None
        
        if not self.client:
            # Fallback: Simple skill-based matching
            return self._fallback_task_matching(available_tasks, agent)
        
        # Prepare data for AI analysis
        tasks_data = [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "priority": t.priority.value,
                "estimated_hours": t.estimated_hours,
                "labels": t.labels,
                "dependencies": t.dependencies
            }
            for t in available_tasks[:10]  # Limit to 10 tasks for context
        ]
        
        agent_data = {
            "id": agent.worker_id,
            "name": agent.name,
            "role": agent.role,
            "skills": agent.skills,
            "current_capacity": agent.capacity,
            "completed_tasks": agent.completed_tasks_count
        }
        
        # Serialize ProjectState dataclass to JSON
        project_state_data = {
            "board_id": project_state.board_id,
            "project_name": project_state.project_name,
            "total_tasks": project_state.total_tasks,
            "completed_tasks": project_state.completed_tasks,
            "in_progress_tasks": project_state.in_progress_tasks,
            "blocked_tasks": project_state.blocked_tasks,
            "progress_percent": project_state.progress_percent,
            "team_velocity": project_state.team_velocity,
            "risk_level": project_state.risk_level.value if hasattr(project_state.risk_level, 'value') else str(project_state.risk_level),
            "last_updated": project_state.last_updated.isoformat() if hasattr(project_state.last_updated, 'isoformat') else str(project_state.last_updated)
        }
        
        prompt = self.prompts["task_assignment"].format(
            tasks=json.dumps(tasks_data, indent=2),
            agent=json.dumps(agent_data, indent=2),
            project_state=json.dumps(project_state_data, indent=2)
        )
        
        try:
            response = await self._call_claude(prompt)
            result = json.loads(response)
            
            # Find the recommended task
            task_id = result.get("recommended_task_id")
            for task in available_tasks:
                if task.id == task_id:
                    return task
                    
        except Exception as e:
            print(f"AI task matching failed: {e}", file=sys.stderr)
        
        # Fallback to simple matching
        return self._fallback_task_matching(available_tasks, agent)
    
    def _fallback_task_matching(self, tasks: List[Task], agent: WorkerStatus) -> Optional[Task]:
        """
        Simple skill-based task matching without AI.
        
        Parameters
        ----------
        tasks : List[Task]
            Available tasks to match
        agent : WorkerStatus
            Agent to match tasks for
        
        Returns
        -------
        Optional[Task]
            Best matching task based on priority and skills
        
        Notes
        -----
        Scores tasks based on:
        - Priority (urgent=4, high=3, medium=2, low=1)
        - Skill matches (2 points per matching skill)
        """
        # Score tasks based on priority and skill match
        best_score = -1
        best_task = None
        
        priority_scores = {
            Priority.URGENT: 10,  # Heavily prioritize urgent tasks in fallback mode
            Priority.HIGH: 3,
            Priority.MEDIUM: 2,
            Priority.LOW: 1
        }
        
        for task in tasks:
            score = priority_scores.get(task.priority, 1)
            
            # Check skill match
            if agent.skills and task.labels:
                skill_match = len(set(agent.skills) & set(task.labels))
                score += skill_match * 2
            
            if score > best_score:
                best_score = score
                best_task = task
        
        return best_task
    
    async def generate_task_instructions(
        self, 
        task: Task, 
        agent: Optional[WorkerStatus] = None
    ) -> str:
        """
        Generate detailed instructions for a task.
        
        Parameters
        ----------
        task : Task
            The task to generate instructions for
        agent : Optional[WorkerStatus], default=None
            The agent assigned to the task
        
        Returns
        -------
        str
            Detailed task instructions formatted as markdown
        
        Examples
        --------
        >>> instructions = await engine.generate_task_instructions(task, agent)
        >>> print(instructions)
        ## Task Assignment for Alice
        ...
        
        Notes
        -----
        Uses AI to generate context-aware instructions when available,
        otherwise provides structured fallback instructions.
        """
        if not self.client:
            # Fallback instructions when AI is not available
            return self._generate_fallback_instructions(task, agent)
        
        task_data = {
            "name": task.name,
            "description": task.description,
            "priority": task.priority.value,
            "estimated_hours": task.estimated_hours,
            "dependencies": task.dependencies,
            "labels": task.labels
        }
        
        agent_data = {
            "name": agent.name if agent else "Unknown",
            "role": agent.role if agent else "Developer",
            "skills": agent.skills if agent else []
        }
        
        prompt = self.prompts["task_instructions"].format(
            task=json.dumps(task_data, indent=2),
            agent=json.dumps(agent_data, indent=2)
        )
        
        try:
            instructions = await self._call_claude(prompt)
            return instructions
        except Exception as e:
            print(f"AI instruction generation failed: {e}", file=sys.stderr)
            return self._generate_fallback_instructions(task, agent)
    
    def _generate_fallback_instructions(self, task: Task, agent: Optional[WorkerStatus]) -> str:
        """
        Generate fallback instructions when AI is not available.
        
        Parameters
        ----------
        task : Task
            Task to generate instructions for
        agent : Optional[WorkerStatus]
            Agent assigned to the task
        
        Returns
        -------
        str
            Structured task instructions in markdown format
        """
        agent_name = agent.name if agent else "Team Member"
        
        return f"""## Task Assignment for {agent_name}

**Task:** {task.name}

**Description:** {task.description}

**Priority:** {task.priority.value}
**Estimated Hours:** {task.estimated_hours}

### Instructions:

1. **Review Requirements**
   - Read the task description carefully
   - Check any linked documentation
   - Identify dependencies: {', '.join(task.dependencies) if task.dependencies else 'None'}

2. **Implementation Steps**
   - Break down the task into smaller subtasks
   - Start with the core functionality
   - Follow project coding standards
   - Write tests as you go

3. **Definition of Done**
   - All requirements from description are met
   - Code is tested and reviewed
   - Documentation is updated
   - No known bugs or issues

4. **Communication**
   - Report progress regularly
   - Ask for clarification if needed
   - Report any blockers immediately

**Labels:** {', '.join(task.labels) if task.labels else 'None'}

Good luck with your task!"""
    
    async def analyze_blocker(
        self,
        task_id: str,
        description: str,
        severity: str,
        agent: Optional['WorkerStatus'] = None,
        task: Optional['Task'] = None
    ) -> Dict[str, Any]:
        """
        Analyze a blocker and suggest resolution steps.
        
        Parameters
        ----------
        task_id : str
            ID of the blocked task
        description : str
            Detailed description of the blocker
        severity : str
            Severity level (low, medium, high, urgent)
        agent : Optional[WorkerStatus]
            Agent who reported the blocker (for context-aware suggestions)
        task : Optional[Task]
            Full task details (for enhanced analysis)
        
        Returns
        -------
        Dict[str, Any]
            Analysis results including:
            - root_cause: Identified cause
            - impact_assessment: Impact description
            - resolution_steps: List of steps tailored to agent skills
            - required_resources: Needed resources
            - estimated_hours: Time to resolve
            - escalation_needed: Boolean
            - prevention_measures: Future prevention steps
            - learning_opportunities: Skills/knowledge gaps identified
            - recommended_collaborators: Team members who could help
        
        Examples
        --------
        >>> analysis = await engine.analyze_blocker(
        ...     "TASK-123", 
        ...     "Database connection timeout",
        ...     "high",
        ...     agent=worker_status,
        ...     task=task_obj
        ... )
        >>> print(analysis['resolution_steps'])
        ['Check database server status', ...]
        """
        if not self.client:
            return self._generate_fallback_blocker_analysis(description, severity, agent, task)
        
        # Prepare agent context
        agent_context = ""
        if agent:
            agent_context = f"""
Agent Profile:
- ID: {agent.worker_id}
- Name: {agent.name}
- Role: {agent.role}
- Skills: {', '.join(agent.skills) if agent.skills else 'None specified'}
- Current Tasks: {len(agent.current_tasks)} active tasks
- Completed Tasks: {agent.completed_tasks_count}
- Performance Score: {agent.performance_score}
"""
        
        # Prepare task context
        task_context = ""
        if task:
            task_context = f"""
Task Details:
- Name: {task.name}
- Description: {task.description}
- Priority: {task.priority.value if task.priority else 'Not set'}
- Estimated Hours: {task.estimated_hours}
- Dependencies: {', '.join(task.dependencies) if task.dependencies else 'None'}
- Labels: {', '.join(task.labels) if task.labels else 'None'}
"""
        
        prompt = self.prompts["blocker_analysis"].format(
            task_id=task_id,
            description=description,
            severity=severity,
            agent_context=agent_context,
            task_context=task_context
        )
        
        try:
            response = await self._call_claude(prompt)
            return json.loads(response)
        except Exception as e:
            print(f"AI blocker analysis failed: {e}", file=sys.stderr)
            return self._generate_fallback_blocker_analysis(description, severity, agent, task)
    
    def _generate_fallback_blocker_analysis(
        self, 
        description: str, 
        severity: str,
        agent: Optional['WorkerStatus'] = None,
        task: Optional['Task'] = None
    ) -> Dict[str, Any]:
        """
        Generate fallback blocker analysis without AI.
        
        Parameters
        ----------
        description : str
            Blocker description
        severity : str
            Severity level
        agent : Optional[WorkerStatus]
            Agent who reported the blocker
        task : Optional[Task]
            Task details
        
        Returns
        -------
        Dict[str, Any]
            Basic analysis with agent-aware resolution steps
        """
        # Basic analysis
        base_steps = [
            "Review the blocker description",
            "Identify required resources",
            "Research potential solutions",
            "Document resolution steps"
        ]
        
        # Add agent-specific guidance if available
        if agent and agent.skills:
            skill_based_steps = []
            if "python" in [s.lower() for s in agent.skills]:
                skill_based_steps.append("Check Python documentation and Stack Overflow")
            if "database" in [s.lower() for s in agent.skills]:
                skill_based_steps.append("Review database logs and connection settings")
            if "frontend" in [s.lower() for s in agent.skills]:
                skill_based_steps.append("Check browser console and network requests")
            
            if skill_based_steps:
                base_steps = skill_based_steps + base_steps
        
        # Adjust resources based on agent experience
        resources = ["Team lead", "Subject matter expert"]
        if agent and agent.performance_score < 0.7:
            resources.insert(0, "Senior developer (mentoring)")
        
        return {
            "root_cause": "Analysis needed",
            "impact_assessment": f"Blocker reported: {description}",
            "resolution_steps": base_steps,
            "required_resources": resources,
            "estimated_hours": 2 if severity == "low" else 4,
            "escalation_needed": severity in ["high", "urgent"],
            "prevention_measures": [
                "Improve documentation",
                "Add monitoring",
                "Review process"
            ],
            "learning_opportunities": ["Root cause analysis", "Problem solving"],
            "recommended_collaborators": ["Team lead", "Senior developer"],
            "skill_match_confidence": "medium"
        }
    
    async def generate_clarification(
        self,
        task: Task,
        question: str,
        context: str = ""
    ) -> str:
        """
        Generate clarification for a task-related question.
        
        Parameters
        ----------
        task : Task
            The task in question
        question : str
            The question needing clarification
        context : str, optional
            Additional context for the question
        
        Returns
        -------
        str
            Clarification response
        
        Examples
        --------
        >>> clarification = await engine.generate_clarification(
        ...     task,
        ...     "What database should I use?",
        ...     "Working on user authentication"
        ... )
        """
        if not self.client:
            return f"Please clarify: {question}\n\nTask: {task.name}\nContext: {context}"
        
        prompt = f"""Help clarify this question about a task:

Task: {task.name}
Description: {task.description}
Question: {question}
Context: {context}

Provide a helpful clarification that guides the developer."""
        
        try:
            return await self._call_claude(prompt)
        except Exception as e:
            print(f"AI clarification failed: {e}", file=sys.stderr)
            return f"Please clarify: {question}\n\nTask: {task.name}\nContext: {context}"
    
    async def analyze_project_risks(
        self,
        project_state: ProjectState,
        recent_blockers: List[BlockerReport],
        team_status: List[WorkerStatus]
    ) -> List[ProjectRisk]:
        """
        Analyze and identify project risks.
        
        Parameters
        ----------
        project_state : ProjectState
            Current project state
        recent_blockers : List[BlockerReport]
            Recent blockers encountered
        team_status : List[WorkerStatus]
            Current team member status
        
        Returns
        -------
        List[ProjectRisk]
            Identified risks with mitigation strategies
        
        Examples
        --------
        >>> risks = await engine.analyze_project_risks(
        ...     ProjectState.AT_RISK,
        ...     recent_blockers,
        ...     team_status
        ... )
        >>> for risk in risks:
        ...     print(f"{risk.description}: {risk.mitigation}")
        
        Notes
        -----
        Analyzes up to 10 recent blockers to identify patterns.
        Falls back to basic risk assessment if AI unavailable.
        """
        if not self.client:
            return self._generate_fallback_risk_analysis(project_state)
        
        # Prepare data
        blockers_data = [
            {
                "task_id": b.task_id,
                "description": b.description,
                "severity": b.severity.value,
                "reported_at": b.reported_at.isoformat()
            }
            for b in recent_blockers[-10:]  # Last 10 blockers
        ]
        
        team_data = [
            {
                "name": w.name,
                "role": w.role,
                "current_tasks": len(w.current_tasks),
                "capacity": w.capacity
            }
            for w in team_status
        ]
        
        # Serialize ProjectState dataclass to JSON
        project_state_data = {
            "board_id": project_state.board_id,
            "project_name": project_state.project_name,
            "total_tasks": project_state.total_tasks,
            "completed_tasks": project_state.completed_tasks,
            "in_progress_tasks": project_state.in_progress_tasks,
            "blocked_tasks": project_state.blocked_tasks,
            "progress_percent": project_state.progress_percent,
            "team_velocity": project_state.team_velocity,
            "risk_level": project_state.risk_level.value if hasattr(project_state.risk_level, 'value') else str(project_state.risk_level),
            "last_updated": project_state.last_updated.isoformat() if hasattr(project_state.last_updated, 'isoformat') else str(project_state.last_updated)
        }
        
        prompt = self.prompts["project_risk"].format(
            project_state=json.dumps(project_state_data, indent=2),
            recent_blockers=json.dumps(blockers_data, indent=2),
            team_status=json.dumps(team_data, indent=2)
        )
        
        try:
            response = await self._call_claude(prompt)
            result = json.loads(response)
            
            # Convert to ProjectRisk objects
            risks = []
            for risk_data in result.get("risks", []):
                likelihood_map = {
                    "low": 0.2,
                    "medium": 0.5,
                    "high": 0.8
                }
                
                impact_severity = {
                    "low": RiskLevel.LOW,
                    "medium": RiskLevel.MEDIUM,
                    "high": RiskLevel.HIGH
                }
                
                risk = ProjectRisk(
                    risk_type="project",
                    description=risk_data["description"],
                    severity=impact_severity.get(risk_data["impact"], RiskLevel.MEDIUM),
                    probability=likelihood_map.get(risk_data["likelihood"], 0.5),
                    impact=risk_data.get("impact", "Unknown impact"),
                    mitigation_strategy=risk_data["mitigation"],
                    identified_at=datetime.now()
                )
                risks.append(risk)
            
            return risks
            
        except Exception as e:
            print(f"AI risk analysis failed: {e}", file=sys.stderr)
            return self._generate_fallback_risk_analysis(project_state)
    
    def _generate_fallback_risk_analysis(self, project_state: ProjectState) -> List[ProjectRisk]:
        """
        Generate fallback risk analysis without AI.
        
        Parameters
        ----------
        project_state : ProjectState
            Current project state
        
        Returns
        -------
        List[ProjectRisk]
            Basic risks based on project state
        """
        risks = []
        
        if project_state.risk_level == RiskLevel.HIGH:
            risks.append(ProjectRisk(
                risk_type="timeline",
                description="Project timeline at risk",
                severity=RiskLevel.HIGH,
                probability=0.7,
                impact="Potential delays in delivery",
                mitigation_strategy="Review task priorities and resource allocation",
                identified_at=datetime.now()
            ))
        
        return risks
    
    async def analyze_project_health(
        self,
        project_state: ProjectState,
        recent_activities: List[Dict[str, Any]],
        team_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze overall project health using AI.
        
        Parameters
        ----------
        project_state : ProjectState
            Current project state
        recent_activities : List[Dict[str, Any]]
            Recent project activities/events
        team_status : Dict[str, Any]
            Current team status information
            
        Returns
        -------
        Dict[str, Any]
            Project health analysis with overall health, timeline prediction,
            risk factors, recommendations, and resource optimization
        """
        if not self.client:
            return self._generate_fallback_health_analysis(project_state, team_status)
        
        # Serialize ProjectState dataclass to JSON
        project_state_data = {
            "board_id": project_state.board_id,
            "project_name": project_state.project_name,
            "total_tasks": project_state.total_tasks,
            "completed_tasks": project_state.completed_tasks,
            "in_progress_tasks": project_state.in_progress_tasks,
            "blocked_tasks": project_state.blocked_tasks,
            "progress_percent": project_state.progress_percent,
            "team_velocity": project_state.team_velocity,
            "risk_level": project_state.risk_level.value,
            "last_updated": project_state.last_updated.isoformat() if hasattr(project_state.last_updated, 'isoformat') else str(project_state.last_updated),
            "overdue_tasks": len(project_state.overdue_tasks)
        }
        
        # Serialize team status if it's a list of WorkerStatus objects
        if isinstance(team_status, list) and len(team_status) > 0:
            # Assume it's a list of WorkerStatus objects
            team_status_data = [
                {
                    "worker_id": worker.worker_id,
                    "name": worker.name,
                    "role": worker.role,
                    "current_tasks_count": len(worker.current_tasks),
                    "completed_tasks_count": worker.completed_tasks_count,
                    "capacity": worker.capacity,
                    "performance_score": getattr(worker, 'performance_score', 1.0)
                }
                for worker in team_status
            ]
        else:
            team_status_data = team_status
        
        # Create project health analysis prompt
        prompt = f"""Analyze the health of this software project and provide comprehensive insights.

Project State:
{json.dumps(project_state_data, indent=2)}

Recent Activities:
{json.dumps(recent_activities, indent=2)}

Team Status:
{json.dumps(team_status_data, indent=2)}

Provide a detailed analysis including:
1. Overall project health assessment (green/yellow/red)
2. Timeline prediction with confidence level
3. Key risk factors
4. Actionable recommendations
5. Resource optimization suggestions

Return JSON in this format:
{{
    "overall_health": "green|yellow|red",
    "timeline_prediction": {{
        "on_track": true|false,
        "estimated_completion": "date or description",
        "confidence": 0.0-1.0,
        "critical_path_risks": ["risk1", "risk2"]
    }},
    "risk_factors": [
        {{
            "type": "resource|timeline|technical|quality",
            "description": "detailed description",
            "severity": "low|medium|high",
            "mitigation": "suggested action"
        }}
    ],
    "recommendations": [
        {{
            "priority": "high|medium|low",
            "action": "specific action to take",
            "expected_impact": "what this will achieve"
        }}
    ],
    "resource_optimization": [
        {{
            "suggestion": "optimization suggestion",
            "impact": "expected improvement"
        }}
    ]
}}"""
        
        try:
            response = await self._call_claude(prompt)
            result = json.loads(response)
            return result
            
        except Exception as e:
            print(f"AI health analysis failed: {e}", file=sys.stderr)
            return self._generate_fallback_health_analysis(project_state, team_status)
    
    def _generate_fallback_health_analysis(
        self, 
        project_state: ProjectState,
        team_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate fallback health analysis without AI.
        
        Parameters
        ----------
        project_state : ProjectState
            Current project state
        team_status : Dict[str, Any]
            Team status information
            
        Returns
        -------
        Dict[str, Any]
            Basic health analysis based on metrics
        """
        # Determine overall health based on metrics
        overall_health = "green"
        if project_state.risk_level == RiskLevel.HIGH:
            overall_health = "red"
        elif project_state.risk_level == RiskLevel.MEDIUM or project_state.blocked_tasks > 2:
            overall_health = "yellow"
        
        # Calculate timeline prediction
        completion_rate = project_state.completed_tasks / max(project_state.total_tasks, 1)
        on_track = completion_rate >= (project_state.progress_percent / 100.0)
        
        risk_factors = []
        
        # Check for resource risks
        if project_state.blocked_tasks > 0:
            risk_factors.append({
                "type": "resource",
                "description": f"{project_state.blocked_tasks} tasks are currently blocked",
                "severity": "high" if project_state.blocked_tasks > 2 else "medium",
                "mitigation": "Review and resolve blockers urgently"
            })
        
        # Check for timeline risks
        if len(project_state.overdue_tasks) > 0:
            risk_factors.append({
                "type": "timeline",
                "description": f"{len(project_state.overdue_tasks)} tasks are overdue",
                "severity": "high",
                "mitigation": "Reassign or reprioritize overdue tasks"
            })
        
        # Generate recommendations
        recommendations = []
        if project_state.team_velocity < 3.0:
            recommendations.append({
                "priority": "high",
                "action": "Review team capacity and task complexity",
                "expected_impact": "Improve velocity by 20-30%"
            })
        
        if project_state.blocked_tasks > 0:
            recommendations.append({
                "priority": "high",
                "action": "Conduct blocker review session",
                "expected_impact": "Unblock tasks and restore progress"
            })
        
        return {
            "overall_health": overall_health,
            "timeline_prediction": {
                "on_track": on_track,
                "estimated_completion": "Based on current velocity",
                "confidence": 0.6 if on_track else 0.3,
                "critical_path_risks": ["Resource constraints"] if project_state.blocked_tasks > 0 else []
            },
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "resource_optimization": [
                {
                    "suggestion": "Balance workload across team members",
                    "impact": "Reduce bottlenecks and improve throughput"
                }
            ]
        }
    
    async def analyze_feature_request(self, feature_description: str) -> Dict[str, Any]:
        """
        Analyze a feature request and generate appropriate tasks.
        
        Parameters
        ----------
        feature_description : str
            Natural language description of the feature to implement
            
        Returns
        -------
        Dict[str, Any]
            Dictionary containing required tasks with details
            
        Examples
        --------
        >>> result = await engine.analyze_feature_request("Add user profile page")
        >>> tasks = result["required_tasks"]
        """
        # Fallback for when Claude is unavailable
        if not self.client:
            return self._analyze_feature_request_fallback(feature_description)
            
        try:
            prompt = f"""Analyze this feature request and generate a comprehensive task breakdown.

Feature Request: {feature_description}

Generate a detailed task list for implementing this feature. Consider:
1. Design/planning tasks
2. Backend implementation needs
3. Frontend/UI requirements
4. Database/data model changes
5. API endpoints required
6. Security considerations
7. Testing requirements
8. Documentation needs

Return JSON with this exact format:
{{
    "required_tasks": [
        {{
            "name": "specific task name",
            "description": "detailed description of what needs to be done",
            "estimated_hours": integer,
            "labels": ["appropriate", "labels"],
            "critical": true/false,
            "task_type": "design|backend|frontend|database|testing|documentation|security"
        }}
    ],
    "feature_complexity": "simple|moderate|complex",
    "technical_requirements": ["list", "of", "technical", "needs"],
    "dependencies_on_existing": ["authentication", "api", "database"] // existing systems this feature depends on
}}

Be specific and actionable. Each task should be self-contained and assignable to a developer."""

            response = await self._call_claude(prompt)
            
            # Parse JSON response
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract structured data
                print(f"Failed to parse AI response as JSON, using fallback", file=sys.stderr)
                return self._analyze_feature_request_fallback(feature_description)
                
        except Exception as e:
            print(f"AI feature analysis failed: {e}, using fallback", file=sys.stderr)
            return self._analyze_feature_request_fallback(feature_description)
    
    def _analyze_feature_request_fallback(self, feature_description: str) -> Dict[str, Any]:
        """Fallback feature analysis when AI is unavailable."""
        feature_lower = feature_description.lower()
        tasks = []
        
        # Always start with design
        tasks.append({
            "name": f"Design {feature_description}",
            "description": f"Create technical design and architecture for {feature_description}",
            "estimated_hours": 4,
            "labels": ["design", "planning"],
            "critical": False,
            "task_type": "design"
        })
        
        # Analyze feature type and add appropriate tasks
        if any(word in feature_lower for word in ['api', 'endpoint', 'service']):
            tasks.append({
                "name": f"Implement API for {feature_description}",
                "description": f"Build backend API endpoints and business logic",
                "estimated_hours": 12,
                "labels": ["backend", "api"],
                "critical": True,
                "task_type": "backend"
            })
            
        if any(word in feature_lower for word in ['ui', 'page', 'screen', 'interface']):
            tasks.append({
                "name": f"Build UI for {feature_description}",
                "description": f"Create user interface components and interactions",
                "estimated_hours": 10,
                "labels": ["frontend", "ui"],
                "critical": True,
                "task_type": "frontend"
            })
            
        # Always add testing and documentation
        tasks.extend([
            {
                "name": f"Test {feature_description}",
                "description": "Write unit tests and perform integration testing",
                "estimated_hours": 6,
                "labels": ["testing", "qa"],
                "critical": False,
                "task_type": "testing"
            },
            {
                "name": f"Document {feature_description}",
                "description": "Create user and technical documentation",
                "estimated_hours": 3,
                "labels": ["documentation"],
                "critical": False,
                "task_type": "documentation"
            }
        ])
        
        return {
            "required_tasks": tasks,
            "feature_complexity": "moderate",
            "technical_requirements": [],
            "dependencies_on_existing": []
        }
    
    async def analyze_integration_points(
        self, 
        feature_tasks: List[Task], 
        existing_tasks: List[Task]
    ) -> Dict[str, Any]:
        """
        Analyze how new feature tasks should integrate with existing project tasks.
        
        Parameters
        ----------
        feature_tasks : List[Task]
            Tasks for the new feature
        existing_tasks : List[Task]
            Current project tasks
            
        Returns
        -------
        Dict[str, Any]
            Integration analysis including dependencies and phase
            
        Examples
        --------
        >>> integration = await engine.analyze_integration_points(new_tasks, project_tasks)
        >>> phase = integration["suggested_phase"]
        """
        # Fallback for when Claude is unavailable
        if not self.client:
            return self._analyze_integration_fallback(feature_tasks, existing_tasks)
            
        try:
            # Prepare task summaries
            feature_summary = [
                {"name": t.name, "labels": t.labels, "type": getattr(t, 'task_type', 'unknown')}
                for t in feature_tasks
            ]
            
            existing_summary = [
                {
                    "id": t.id,
                    "name": t.name, 
                    "labels": t.labels,
                    "status": t.status.value,
                    "description": t.description[:100] + "..." if len(t.description) > 100 else t.description
                }
                for t in existing_tasks
            ]
            
            prompt = f"""Analyze how these new feature tasks should integrate with the existing project.

New Feature Tasks:
{json.dumps(feature_summary, indent=2)}

Existing Project Tasks:
{json.dumps(existing_summary, indent=2)}

Determine:
1. Which existing tasks the new feature depends on (by task ID)
2. The appropriate project phase for these tasks
3. Integration complexity and risks
4. Recommended task ordering

Return JSON with this format:
{{
    "dependent_task_ids": ["list", "of", "existing", "task", "ids"],
    "suggested_phase": "initial|development|testing|deployment|maintenance",
    "integration_complexity": "low|medium|high",
    "confidence": 0.0-1.0,
    "integration_risks": ["list", "of", "potential", "issues"],
    "recommendations": [
        {{
            "type": "dependency|ordering|resource",
            "description": "specific recommendation"
        }}
    ],
    "rationale": "explanation of integration approach"
}}"""

            response = await self._call_claude(prompt)
            
            # Parse JSON response
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                print(f"Failed to parse AI response as JSON, using fallback", file=sys.stderr)
                return self._analyze_integration_fallback(feature_tasks, existing_tasks)
                
        except Exception as e:
            print(f"AI integration analysis failed: {e}, using fallback", file=sys.stderr)
            return self._analyze_integration_fallback(feature_tasks, existing_tasks)
    
    def _analyze_integration_fallback(self, feature_tasks: List[Task], existing_tasks: List[Task]) -> Dict[str, Any]:
        """Fallback integration analysis when AI is unavailable."""
        # Analyze existing task states
        completed = [t for t in existing_tasks if t.status.value == "done"]
        in_progress = [t for t in existing_tasks if t.status.value == "in_progress"]
        
        # Find potential dependencies based on labels
        dependent_ids = []
        for existing in existing_tasks:
            for feature in feature_tasks:
                # Check for label overlap
                if existing.labels and feature.labels:
                    if set(existing.labels) & set(feature.labels):
                        dependent_ids.append(existing.id)
                        break
        
        # Determine phase
        if len(completed) == 0:
            phase = "initial"
        elif len(completed) / len(existing_tasks) > 0.8:
            phase = "maintenance"
        elif any("test" in t.name.lower() for t in in_progress):
            phase = "testing"
        else:
            phase = "development"
            
        return {
            "dependent_task_ids": list(set(dependent_ids)),
            "suggested_phase": phase,
            "integration_complexity": "medium",
            "confidence": 0.7,
            "integration_risks": [],
            "recommendations": [],
            "rationale": "Based on task label matching and project progress"
        }
    
    async def _call_claude(self, prompt: str) -> str:
        """
        Call Claude API with error handling.
        
        Parameters
        ----------
        prompt : str
            The prompt to send to Claude
        
        Returns
        -------
        str
            Claude's response text
        
        Raises
        ------
        Exception
            If the API call fails or client is unavailable
        """
        if not self.client:
            raise Exception("Anthropic client not available")
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"Error calling Claude: {e}", file=sys.stderr)
            raise