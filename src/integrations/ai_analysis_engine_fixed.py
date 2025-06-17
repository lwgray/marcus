"""
AI-powered analysis and decision engine for PM Agent.

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
            # Get API key from environment
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                print("⚠️  ANTHROPIC_API_KEY not found - AI features will use fallback mode", file=sys.stderr)
                self.client = None
            else:
                # Try different initialization approaches based on version
                try:
                    # First try with just api_key (works with most versions)
                    self.client = anthropic.Anthropic(api_key=api_key)
                except TypeError as e:
                    if "proxies" in str(e):
                        # If it expects proxies, provide None
                        try:
                            self.client = anthropic.Anthropic(api_key=api_key, proxies=None)
                        except:
                            # If that fails too, try with empty dict
                            self.client = anthropic.Anthropic(api_key=api_key, proxies={})
                    else:
                        raise
                
                print("✅ Anthropic client initialized successfully", file=sys.stderr)
                
        except Exception as e:
            print(f"⚠️  Failed to initialize Anthropic client: {e}", file=sys.stderr)
            print("   AI features will use fallback responses", file=sys.stderr)
            self.client = None
        
        self.model: str = "claude-3-sonnet-20241022"  # Using Sonnet for speed/cost balance
        
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

Provide JSON response:
{{
    "root_cause": "analysis",
    "impact_assessment": "description",
    "resolution_steps": ["step1", "step2"],
    "required_resources": ["resource1"],
    "estimated_hours": number,
    "escalation_needed": boolean,
    "prevention_measures": ["measure1"]
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
        
        prompt = self.prompts["task_assignment"].format(
            tasks=json.dumps(tasks_data, indent=2),
            agent=json.dumps(agent_data, indent=2),
            project_state=project_state.value
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
            Priority.URGENT: 4,
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
        severity: str
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
        
        Returns
        -------
        Dict[str, Any]
            Analysis results including:
            - root_cause: Identified cause
            - impact_assessment: Impact description
            - resolution_steps: List of steps
            - required_resources: Needed resources
            - estimated_hours: Time to resolve
            - escalation_needed: Boolean
            - prevention_measures: Future prevention steps
        
        Examples
        --------
        >>> analysis = await engine.analyze_blocker(
        ...     "TASK-123", 
        ...     "Database connection timeout",
        ...     "high"
        ... )
        >>> print(analysis['resolution_steps'])
        ['Check database server status', ...]
        """
        if not self.client:
            return self._generate_fallback_blocker_analysis(description, severity)
        
        prompt = self.prompts["blocker_analysis"].format(
            task_id=task_id,
            description=description,
            severity=severity
        )
        
        try:
            response = await self._call_claude(prompt)
            return json.loads(response)
        except Exception as e:
            print(f"AI blocker analysis failed: {e}", file=sys.stderr)
            return self._generate_fallback_blocker_analysis(description, severity)
    
    def _generate_fallback_blocker_analysis(self, description: str, severity: str) -> Dict[str, Any]:
        """
        Generate fallback blocker analysis without AI.
        
        Parameters
        ----------
        description : str
            Blocker description
        severity : str
            Severity level
        
        Returns
        -------
        Dict[str, Any]
            Basic analysis with generic resolution steps
        """
        return {
            "root_cause": "Analysis needed",
            "impact_assessment": f"Blocker reported: {description}",
            "needs_coordination": severity in ["high", "urgent"],
            "resolution_steps": [
                "Review the blocker description",
                "Identify required resources",
                "Escalate if necessary",
                "Document resolution steps"
            ],
            "required_resources": ["Team lead", "Subject matter expert"],
            "estimated_hours": 2 if severity == "low" else 4,
            "escalation_needed": severity in ["high", "urgent"],
            "prevention_measures": [
                "Improve documentation",
                "Add monitoring",
                "Review process"
            ]
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
        
        prompt = self.prompts["project_risk"].format(
            project_state=project_state.value,
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
        
        if project_state == ProjectState.AT_RISK:
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