import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

import anthropic

from src.core.models import (
    Task, WorkerStatus, ProjectState, 
    RiskLevel, Priority, BlockerReport, ProjectRisk
)


class AIAnalysisEngine:
    """AI-powered analysis and decision engine using Claude"""
    
    def __init__(self):
        # Initialize Anthropic client with better error handling
        try:
            # Get API key from environment
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
            # Initialize client with minimal parameters to avoid conflicts
            self.client = anthropic.Anthropic(
                api_key=api_key
            )
            
        except Exception as e:
            print(f"Failed to initialize Anthropic client: {e}")
            # Create a mock client for testing
            self.client = None
        
        self.model = "claude-3-sonnet-20241022"  # Using Sonnet for speed/cost balance
        
        # Analysis prompts
        self.prompts = {
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
5. Team collaboration needs

Return your analysis as JSON:
{{
    "recommended_task_id": "task_id",
    "confidence_score": 0.0-1.0,
    "reasoning": "explanation",
    "alternative_tasks": ["task_id1", "task_id2"],
    "considerations": ["factor1", "factor2"]
}}""",

            "task_instructions": """You are an AI Project Manager providing detailed task instructions.

Task: {task}
Assigned to: {agent}

Generate comprehensive instructions that include:
1. Clear objectives and success criteria
2. Step-by-step approach recommendations
3. Technical considerations and best practices
4. Resources and documentation references
5. Potential challenges and solutions
6. Collaboration touchpoints

Make instructions specific, actionable, and tailored to the agent's skill level.""",

            "blocker_analysis": """You are an AI Project Manager analyzing a blocker.

Task: {task_id}
Blocker: {description}
Severity: {severity}

Analyze this blocker and provide:
{{
    "root_cause": "analysis",
    "impact_assessment": "description",
    "needs_coordination": true/false,
    "resolution_steps": ["step1", "step2"],
    "required_resources": ["resource1", "resource2"],
    "estimated_hours": X,
    "escalation_needed": true/false,
    "prevention_measures": ["measure1", "measure2"]
}}""",

            "project_analysis": """You are an AI Project Manager analyzing project health.

Project State: {project_state}
Recent Activities: {activities}
Team Status: {team_status}

Provide comprehensive analysis:
{{
    "overall_health": "green/yellow/red",
    "progress_assessment": "description",
    "risk_factors": [
        {{"type": "timeline/resource/technical", "severity": "high/medium/low", "description": "details"}}
    ],
    "recommendations": [
        {{"action": "description", "priority": "high/medium/low", "owner": "role"}}
    ],
    "timeline_prediction": {{
        "on_track": true/false,
        "estimated_completion": "date",
        "confidence": 0.0-1.0
    }},
    "resource_optimization": [
        {{"suggestion": "description", "impact": "description"}}
    ]
}}"""
        }
    
    async def initialize(self):
        """Initialize the AI engine"""
        if not self.client:
            print("⚠️  AI Engine running in mock mode (Anthropic client not available)")
            return
        
        # Test connection
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            print("✅ AI Engine initialized successfully")
        except Exception as e:
            print(f"⚠️  AI Engine test failed: {e}")
            print("   Will use fallback responses")
    
    async def match_task_to_agent(
        self, 
        available_tasks: List[Task], 
        agent: WorkerStatus,
        project_state: ProjectState
    ) -> Optional[Task]:
        """Find the optimal task for an agent"""
        if not available_tasks:
            return None
        
        # For MVP: Simple fallback - highest priority task
        priority_map = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        return max(available_tasks, key=lambda t: priority_map.get(t.priority.value, 1))
    
    async def generate_task_instructions(
        self,
        task: Task,
        agent: Optional[WorkerStatus]
    ) -> str:
        """Generate detailed instructions for a task"""
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
            print(f"AI instruction generation failed: {e}")
            return self._generate_fallback_instructions(task, agent)
    
    def _generate_fallback_instructions(self, task: Task, agent: Optional[WorkerStatus]) -> str:
        """Generate fallback instructions when AI is not available"""
        agent_name = agent.name if agent else "Team Member"
        
        return f"""## Task Assignment for {agent_name}

**Task:** {task.name}

**Description:** {task.description}

**Priority:** {task.priority.value.upper()}

**Estimated Time:** {task.estimated_hours} hours

### Objectives:
Complete this task according to the requirements described above.

### Approach:
1. Review the task description carefully
2. Break down the work into smaller steps
3. Implement according to best practices
4. Test your work thoroughly
5. Document any important decisions

### Definition of Done:
- All requirements in the description are satisfied
- Work is tested and ready for review
- Any necessary documentation is updated

### Need Help?
If you encounter any blockers or need clarification, please report them using the blocker reporting system.

---
*Generated by PM Agent MVP*"""
    
    async def analyze_blocker(
        self,
        task_id: str,
        description: str,
        severity: str
    ) -> Dict[str, Any]:
        """Analyze a blocker and suggest resolution"""
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
            print(f"AI blocker analysis failed: {e}")
            return self._generate_fallback_blocker_analysis(description, severity)
    
    def _generate_fallback_blocker_analysis(self, description: str, severity: str) -> Dict[str, Any]:
        """Generate fallback blocker analysis"""
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
        agent_id: str
    ) -> str:
        """Generate clarification for a task-related question"""
        if not self.client:
            return f"""Clarification needed for task: {task.name}

Question: {question}

Please review the task description and requirements. If you still need clarification, please escalate to your team lead or check the project documentation.

Task details:
- Name: {task.name}
- Description: {task.description}
- Priority: {task.priority.value}"""
        
        prompt = f"""You are an AI Project Manager providing clarification.

Task: {task.name}
Description: {task.description}
Agent: {agent_id}
Question: {question}

Provide a clear, helpful, and specific answer that helps the agent proceed with their work.
Include any relevant context, examples, or references that would be helpful."""
        
        try:
            clarification = await self._call_claude(prompt)
            return clarification
        except:
            return f"Please check the task description for '{task.name}' and escalate to team lead if needed."
    
    async def analyze_project_health(
        self,
        project_state: ProjectState,
        recent_activities: List[Dict[str, Any]],
        team_status: List[WorkerStatus]
    ) -> Dict[str, Any]:
        """Analyze overall project health and provide recommendations"""
        # Fallback analysis based on simple metrics
        return {
            "overall_health": "green" if project_state.progress_percent > 70 else "yellow",
            "progress_assessment": f"Project is {project_state.progress_percent}% complete",
            "risk_factors": [],
            "recommendations": [
                {"action": "Continue current progress", "priority": "medium", "owner": "team"}
            ],
            "timeline_prediction": {
                "on_track": project_state.progress_percent > 50,
                "estimated_completion": "On track",
                "confidence": 0.7
            },
            "resource_optimization": []
        }
    
    async def suggest_blocker_resolution(
        self,
        blocker: BlockerReport
    ) -> Dict[str, Any]:
        """Suggest resolution strategy for a blocker"""
        analysis = await self.analyze_blocker(
            blocker.task_id,
            blocker.description,
            blocker.severity.value
        )
        
        return {
            "blocker_id": blocker.task_id,
            "strategy": analysis["resolution_steps"],
            "required_actions": analysis["required_resources"],
            "estimated_time": analysis["estimated_hours"],
            "escalation_needed": analysis["escalation_needed"]
        }
    
    async def _call_claude(self, prompt: str) -> str:
        """Make a call to Claude API"""
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
            print(f"Error calling Claude: {e}")
            raise
