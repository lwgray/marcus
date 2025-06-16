import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from src.core.models import (
    ProjectState, Task, TaskStatus, RiskLevel,
    BlockerReport, ProjectRisk
)
from src.integrations.mcp_kanban_client import MCPKanbanClient
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.config.settings import Settings


class ProjectMonitor:
    """Continuous monitoring system for project health"""
    
    def __init__(self):
        self.settings = Settings()
        self.kanban_client = MCPKanbanClient()
        self.ai_engine = AIAnalysisEngine()
        
        # State tracking
        self.current_state: Optional[ProjectState] = None
        self.blockers: List[BlockerReport] = []
        self.risks: List[ProjectRisk] = []
        self.historical_data: List[Dict] = []
        
        # Monitoring configuration
        self.check_interval = self.settings.get("monitoring_interval", 900)  # 15 minutes
        self.is_monitoring = False
    
    async def start_monitoring(self):
        """Start the continuous monitoring loop"""
        self.is_monitoring = True
        
        while self.is_monitoring:
            try:
                # Collect project data
                await self._collect_project_data()
                
                # Analyze project health
                await self._analyze_project_health()
                
                # Check for issues
                await self._check_for_issues()
                
                # Store historical data
                self._record_metrics()
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)
    
    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.is_monitoring = False
    
    async def get_project_state(self) -> ProjectState:
        """Get current project state"""
        if not self.current_state:
            await self._collect_project_data()
        return self.current_state
    
    async def _collect_project_data(self):
        """Collect comprehensive project data from kanban board"""
        # Get board summary
        summary = await self.kanban_client.get_board_summary()
        
        # Get all tasks
        all_tasks = await self._get_all_tasks()
        
        # Calculate metrics
        total_tasks = len(all_tasks)
        completed_tasks = len([t for t in all_tasks if t.status == TaskStatus.DONE])
        in_progress_tasks = len([t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS])
        blocked_tasks = len([t for t in all_tasks if t.status == TaskStatus.BLOCKED])
        
        # Find overdue tasks
        overdue_tasks = []
        now = datetime.now()
        for task in all_tasks:
            if task.due_date and task.due_date < now and task.status != TaskStatus.DONE:
                overdue_tasks.append(task)
        
        # Calculate progress
        progress_percent = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Calculate velocity (tasks completed per week)
        velocity = await self._calculate_velocity(all_tasks)
        
        # Determine risk level
        risk_level = self._assess_risk_level(
            progress_percent, 
            len(overdue_tasks), 
            blocked_tasks,
            velocity
        )
        
        # Update current state
        self.current_state = ProjectState(
            board_id=self.kanban_client.board_id or "unknown",
            project_name=summary.get("name", "Unknown Project"),
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            blocked_tasks=blocked_tasks,
            progress_percent=progress_percent,
            overdue_tasks=overdue_tasks,
            team_velocity=velocity,
            risk_level=risk_level,
            last_updated=datetime.now()
        )
    
    async def _get_all_tasks(self) -> List[Task]:
        """Get all tasks from all columns"""
        all_tasks = []
        
        columns = ["TODO", "IN PROGRESS", "BLOCKED", "DONE"]
        for column in columns:
            cards = await self.kanban_client._call_tool("mcp_kanban_card_manager", {
                "action": "get_all",
                "boardId": self.kanban_client.board_id,
                "columnName": column
            })
            
            for card in cards:
                task = self.kanban_client._card_to_task(card)
                all_tasks.append(task)
        
        return all_tasks
    
    async def _calculate_velocity(self, tasks: List[Task]) -> float:
        """Calculate team velocity (tasks completed per week)"""
        one_week_ago = datetime.now() - timedelta(days=7)
        
        completed_this_week = [
            t for t in tasks 
            if t.status == TaskStatus.DONE and t.updated_at > one_week_ago
        ]
        
        return len(completed_this_week)
    
    def _assess_risk_level(
        self,
        progress: float,
        overdue_count: int,
        blocked_count: int,
        velocity: float
    ) -> RiskLevel:
        """Assess overall project risk level"""
        risk_score = 0
        
        # Progress-based risk
        if progress < 25:
            risk_score += 2
        elif progress < 50:
            risk_score += 1
        
        # Overdue tasks risk
        if overdue_count > 5:
            risk_score += 3
        elif overdue_count > 2:
            risk_score += 2
        elif overdue_count > 0:
            risk_score += 1
        
        # Blocked tasks risk
        if blocked_count > 3:
            risk_score += 2
        elif blocked_count > 0:
            risk_score += 1
        
        # Velocity risk
        if velocity < 2:
            risk_score += 2
        elif velocity < 5:
            risk_score += 1
        
        # Map score to risk level
        if risk_score >= 6:
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def _analyze_project_health(self):
        """Perform AI-powered project health analysis"""
        if not self.current_state:
            return
        
        # Get recent activities from historical data
        recent_activities = self.historical_data[-10:] if self.historical_data else []
        
        # Get team status (simplified for now)
        team_status = []  # Would be populated from agent status tracking
        
        # Get AI analysis
        analysis = await self.ai_engine.analyze_project_health(
            self.current_state,
            recent_activities,
            team_status
        )
        
        # Extract risks from analysis
        self.risks = []
        for risk_data in analysis.get("risk_factors", []):
            risk = ProjectRisk(
                risk_type=risk_data["type"],
                description=risk_data["description"],
                severity=self._map_severity(risk_data["severity"]),
                probability=0.5,  # Default probability
                impact=risk_data.get("impact", "Medium"),
                mitigation_strategy=risk_data.get("mitigation", "Monitor closely"),
                identified_at=datetime.now()
            )
            self.risks.append(risk)
    
    async def _check_for_issues(self):
        """Check for various project issues"""
        if not self.current_state:
            return
        
        # Check for stalled tasks
        await self._check_stalled_tasks()
        
        # Check for capacity issues
        await self._check_capacity_issues()
        
        # Check for dependency bottlenecks
        await self._check_dependency_bottlenecks()
    
    async def _check_stalled_tasks(self):
        """Identify tasks that haven't progressed"""
        tasks = await self._get_all_tasks()
        
        stall_threshold = timedelta(hours=self.settings.get("stall_threshold_hours", 24))
        now = datetime.now()
        
        for task in tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                if now - task.updated_at > stall_threshold:
                    # Task is stalled, create a risk
                    risk = ProjectRisk(
                        risk_type="stalled_task",
                        description=f"Task '{task.name}' has been in progress for over {stall_threshold.total_seconds()/3600} hours",
                        severity=RiskLevel.MEDIUM,
                        probability=1.0,
                        impact="Delays project timeline",
                        mitigation_strategy="Check in with assigned agent",
                        identified_at=now
                    )
                    self.risks.append(risk)
    
    async def _check_capacity_issues(self):
        """Check if team capacity is being exceeded"""
        # This would integrate with agent status tracking
        # For now, we'll check task distribution
        
        tasks = await self._get_all_tasks()
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        
        if len(in_progress) > 10:  # Configurable threshold
            risk = ProjectRisk(
                risk_type="capacity",
                description="Too many tasks in progress simultaneously",
                severity=RiskLevel.HIGH,
                probability=0.8,
                impact="Team burnout and quality issues",
                mitigation_strategy="Prioritize and defer lower priority tasks",
                identified_at=datetime.now()
            )
            self.risks.append(risk)
    
    async def _check_dependency_bottlenecks(self):
        """Identify dependency chains causing bottlenecks"""
        tasks = await self._get_all_tasks()
        
        # Find blocked tasks with many dependents
        for task in tasks:
            if task.status == TaskStatus.BLOCKED:
                dependents = await self.kanban_client.get_dependent_tasks(task.id)
                if len(dependents) > 2:
                    risk = ProjectRisk(
                        risk_type="dependency",
                        description=f"Task '{task.name}' is blocking {len(dependents)} other tasks",
                        severity=RiskLevel.HIGH,
                        probability=1.0,
                        impact="Multiple tasks cannot proceed",
                        mitigation_strategy="Prioritize unblocking this task",
                        identified_at=datetime.now()
                    )
                    self.risks.append(risk)
    
    def _record_metrics(self):
        """Record current metrics for historical tracking"""
        if self.current_state:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "progress": self.current_state.progress_percent,
                "velocity": self.current_state.team_velocity,
                "blocked_tasks": self.current_state.blocked_tasks,
                "risk_level": self.current_state.risk_level.value,
                "total_tasks": self.current_state.total_tasks,
                "completed_tasks": self.current_state.completed_tasks
            }
            
            self.historical_data.append(metrics)
            
            # Keep only last 100 entries
            if len(self.historical_data) > 100:
                self.historical_data = self.historical_data[-100:]
    
    async def record_blocker(
        self,
        agent_id: str,
        task_id: str,
        description: str
    ) -> BlockerReport:
        """Record a new blocker"""
        blocker = BlockerReport(
            task_id=task_id,
            reporter_id=agent_id,
            description=description,
            severity=RiskLevel.MEDIUM,
            reported_at=datetime.now()
        )
        
        self.blockers.append(blocker)
        return blocker
    
    def _map_severity(self, severity_str: str) -> RiskLevel:
        """Map string severity to RiskLevel enum"""
        mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL
        }
        return mapping.get(severity_str.lower(), RiskLevel.MEDIUM)
    
    def get_current_risks(self) -> List[ProjectRisk]:
        """Get current project risks"""
        return self.risks
    
    def get_active_blockers(self) -> List[BlockerReport]:
        """Get active blockers"""
        return [b for b in self.blockers if not b.resolved]