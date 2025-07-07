"""
MCP Tools for Pipeline Enhancement Features

Exposes pipeline replay, what-if analysis, comparison, monitoring, 
error prediction, and recommendation features through MCP interface.
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from src.visualization.pipeline_replay import PipelineReplayController
from src.analysis.what_if_engine import WhatIfAnalysisEngine, PipelineModification
from src.analysis.pipeline_comparison import PipelineComparator
from src.reports.pipeline_report_generator import PipelineReportGenerator
from src.monitoring.live_pipeline_monitor import LivePipelineMonitor
from src.monitoring.error_predictor import PipelineErrorPredictor
from src.recommendations.recommendation_engine import PipelineRecommendationEngine


class PipelineEnhancementTools:
    """MCP tools for pipeline enhancement features."""
    
    def __init__(self):
        """Initialize all enhancement components."""
        self.replay_controller = None
        self.what_if_engine = None
        self.comparator = PipelineComparator()
        self.report_generator = PipelineReportGenerator()
        self.live_monitor = LivePipelineMonitor()
        self.error_predictor = PipelineErrorPredictor()
        self.recommendation_engine = PipelineRecommendationEngine()
        
    # ==================== Phase 3.1: Pipeline Replay ====================
    
    async def start_replay(self, flow_id: str) -> Dict[str, Any]:
        """
        Start replay session for a pipeline flow.
        
        Tool: pipeline_replay_start
        """
        try:
            self.replay_controller = PipelineReplayController(flow_id)
            
            return {
                "success": True,
                "flow_id": flow_id,
                "total_events": self.replay_controller.max_position,
                "current_position": self.replay_controller.current_position,
                "state": self.replay_controller.get_current_state()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def replay_step_forward(self) -> Dict[str, Any]:
        """
        Step forward in pipeline replay.
        
        Tool: pipeline_replay_forward
        """
        if not self.replay_controller:
            return {"success": False, "error": "No active replay session"}
            
        success, state = self.replay_controller.step_forward()
        return {
            "success": success,
            "state": state,
            "has_more": self.replay_controller.current_position < self.replay_controller.max_position - 1
        }
        
    async def replay_step_backward(self) -> Dict[str, Any]:
        """
        Step backward in pipeline replay.
        
        Tool: pipeline_replay_backward
        """
        if not self.replay_controller:
            return {"success": False, "error": "No active replay session"}
            
        success, state = self.replay_controller.step_backward()
        return {
            "success": success,
            "state": state,
            "has_previous": self.replay_controller.current_position > 0
        }
        
    async def replay_jump_to(self, position: int) -> Dict[str, Any]:
        """
        Jump to specific position in replay.
        
        Tool: pipeline_replay_jump
        """
        if not self.replay_controller:
            return {"success": False, "error": "No active replay session"}
            
        success, state = self.replay_controller.jump_to_position(position)
        return {"success": success, "state": state}
        
    # ==================== Phase 3.2: What-If Analysis ====================
    
    async def start_what_if_analysis(self, flow_id: str) -> Dict[str, Any]:
        """
        Start what-if analysis session.
        
        Tool: what_if_start
        """
        try:
            self.what_if_engine = WhatIfAnalysisEngine(flow_id)
            
            return {
                "success": True,
                "flow_id": flow_id,
                "original_metrics": {
                    "task_count": self.what_if_engine.original_flow["metrics"]["task_count"],
                    "complexity": self.what_if_engine.original_flow["metrics"]["complexity_score"],
                    "cost": self.what_if_engine.original_flow["metrics"]["total_cost"],
                    "quality": self.what_if_engine.original_flow["metrics"]["quality_score"]
                },
                "modifiable_parameters": self.what_if_engine.get_modifiable_parameters()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def simulate_modification(self, modifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Simulate pipeline with modifications.
        
        Tool: what_if_simulate
        """
        if not self.what_if_engine:
            return {"success": False, "error": "No active what-if session"}
            
        try:
            # Convert dict to PipelineModification objects
            mods = []
            for mod in modifications:
                mods.append(PipelineModification(
                    parameter_type=mod["parameter_type"],
                    parameter_name=mod["parameter_name"],
                    old_value=mod.get("old_value"),
                    new_value=mod["new_value"],
                    description=mod.get("description", "")
                ))
                
            result = await self.what_if_engine.simulate_variation(mods)
            return {"success": True, "simulation": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def compare_what_if_scenarios(self) -> Dict[str, Any]:
        """
        Compare all what-if scenarios.
        
        Tool: what_if_compare
        """
        if not self.what_if_engine:
            return {"success": False, "error": "No active what-if session"}
            
        comparison = self.what_if_engine.compare_all_variations()
        return {"success": True, "comparison": comparison}
        
    # ==================== Phase 3.3: Pipeline Comparison ====================
    
    async def compare_pipelines(self, flow_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple pipeline flows.
        
        Tool: pipeline_compare
        """
        try:
            report = self.comparator.compare_multiple_flows(flow_ids)
            return {
                "success": True,
                "report": {
                    "flow_summaries": report.flow_summaries,
                    "common_patterns": report.common_patterns,
                    "unique_decisions": report.unique_decisions,
                    "performance_comparison": report.performance_comparison,
                    "quality_comparison": report.quality_comparison,
                    "recommendations": report.recommendations
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    # ==================== Phase 3.4: Report Generation ====================
    
    async def generate_report(self, flow_id: str, format: str = "html") -> Dict[str, Any]:
        """
        Generate pipeline report.
        
        Tool: pipeline_report
        """
        try:
            if format == "html":
                content = self.report_generator.generate_html_report(flow_id)
            elif format == "markdown":
                content = self.report_generator.generate_markdown_summary(flow_id)
            elif format == "json":
                content = json.dumps(
                    self.report_generator.generate_executive_summary(flow_id),
                    indent=2,
                    default=str
                )
            else:
                return {"success": False, "error": f"Unsupported format: {format}"}
                
            return {
                "success": True,
                "format": format,
                "content": content,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    # ==================== Phase 4: Live Monitoring ====================
    
    async def get_live_dashboard(self) -> Dict[str, Any]:
        """
        Get live monitoring dashboard data.
        
        Tool: pipeline_monitor_dashboard
        """
        try:
            # Get dashboard data without starting monitoring task
            dashboard_data = self.live_monitor.get_dashboard_data()
            
            return {
                "success": True,
                **dashboard_data
            }
                
            dashboard = self.live_monitor.get_dashboard_data()
            return {"success": True, "dashboard": dashboard}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def track_flow_progress(self, flow_id: str) -> Dict[str, Any]:
        """
        Track specific flow progress.
        
        Tool: pipeline_monitor_flow
        """
        try:
            progress = await self.live_monitor.track_flow_progress(flow_id)
            return {
                "success": True,
                "progress": {
                    "flow_id": progress.flow_id,
                    "percentage": progress.progress_percentage,
                    "stage": progress.current_stage,
                    "eta": progress.eta.isoformat() if progress.eta else None,
                    "health": progress.health_status.status,
                    "issues": progress.health_status.issues
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def predict_failure_risk(self, flow_id: str) -> Dict[str, Any]:
        """
        Predict failure risk for a flow.
        
        Tool: pipeline_predict_risk
        """
        try:
            assessment = self.error_predictor.predict_failure_risk(flow_id)
            return {
                "success": True,
                "risk_assessment": {
                    "flow_id": assessment.flow_id,
                    "overall_risk": assessment.overall_risk,
                    "risk_category": assessment.risk_category,
                    "confidence": assessment.confidence,
                    "factors": [
                        {
                            "factor": f.factor,
                            "risk_level": f.risk_level,
                            "description": f.description,
                            "mitigation": f.mitigation
                        }
                        for f in assessment.factors
                    ],
                    "recommendations": assessment.recommendations
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    # ==================== Phase 5: Recommendations ====================
    
    async def get_recommendations(self, flow_id: str) -> Dict[str, Any]:
        """
        Get recommendations for a pipeline flow.
        
        Tool: pipeline_recommendations
        """
        try:
            recommendations = self.recommendation_engine.get_recommendations(flow_id)
            return {
                "success": True,
                "recommendations": [
                    {
                        "type": rec.type,
                        "confidence": rec.confidence,
                        "message": rec.message,
                        "impact": rec.impact,
                        "supporting_data": rec.supporting_data
                    }
                    for rec in recommendations
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def find_similar_flows(self, flow_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Find similar pipeline flows.
        
        Tool: pipeline_find_similar
        """
        try:
            current_flow = self.recommendation_engine._load_flow_data(flow_id)
            if not current_flow:
                return {"success": False, "error": "Flow not found"}
                
            similar_flows = self.recommendation_engine.find_similar_flows(current_flow)
            
            return {
                "success": True,
                "similar_flows": [
                    {
                        "flow_id": sf["flow"]["flow_id"],
                        "project_name": sf["flow"]["project_name"],
                        "similarity": sf["similarity"]
                    }
                    for sf in similar_flows[:limit]
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Tool registration functions for MCP server
def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get all tool definitions for MCP registration."""
    return [
        {
            "name": "pipeline_replay_start",
            "description": "Start replay session for a pipeline flow",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID to replay"}
                },
                "required": ["flow_id"]
            }
        },
        {
            "name": "pipeline_replay_forward",
            "description": "Step forward in pipeline replay",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "pipeline_replay_backward",
            "description": "Step backward in pipeline replay",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "pipeline_replay_jump",
            "description": "Jump to specific position in replay",
            "input_schema": {
                "type": "object",
                "properties": {
                    "position": {"type": "integer", "description": "Position to jump to"}
                },
                "required": ["position"]
            }
        },
        {
            "name": "what_if_start",
            "description": "Start what-if analysis session",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID to analyze"}
                },
                "required": ["flow_id"]
            }
        },
        {
            "name": "what_if_simulate",
            "description": "Simulate pipeline with modifications",
            "input_schema": {
                "type": "object",
                "properties": {
                    "modifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "parameter_type": {"type": "string"},
                                "parameter_name": {"type": "string"},
                                "new_value": {},
                                "old_value": {},
                                "description": {"type": "string"}
                            },
                            "required": ["parameter_type", "parameter_name", "new_value"]
                        }
                    }
                },
                "required": ["modifications"]
            }
        },
        {
            "name": "what_if_compare",
            "description": "Compare all what-if scenarios",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "pipeline_compare",
            "description": "Compare multiple pipeline flows",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of flow IDs to compare"
                    }
                },
                "required": ["flow_ids"]
            }
        },
        {
            "name": "pipeline_report",
            "description": "Generate pipeline report",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID"},
                    "format": {
                        "type": "string",
                        "enum": ["html", "markdown", "json"],
                        "description": "Report format"
                    }
                },
                "required": ["flow_id"]
            }
        },
        {
            "name": "pipeline_monitor_dashboard",
            "description": "Get live monitoring dashboard data",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "pipeline_monitor_flow",
            "description": "Track specific flow progress",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID to track"}
                },
                "required": ["flow_id"]
            }
        },
        {
            "name": "pipeline_predict_risk",
            "description": "Predict failure risk for a flow",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID to assess"}
                },
                "required": ["flow_id"]
            }
        },
        {
            "name": "pipeline_recommendations",
            "description": "Get recommendations for a pipeline flow",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID"}
                },
                "required": ["flow_id"]
            }
        },
        {
            "name": "pipeline_find_similar",
            "description": "Find similar pipeline flows",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flow_id": {"type": "string", "description": "Flow ID"},
                    "limit": {
                        "type": "integer",
                        "description": "Max similar flows to return",
                        "default": 5
                    }
                },
                "required": ["flow_id"]
            }
        }
    ]


# Initialize tools instance
pipeline_tools = PipelineEnhancementTools()