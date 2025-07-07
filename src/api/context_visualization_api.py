"""
Context Visualization API

Provides endpoints for visualizing task context including dependencies,
implementations, and architectural decisions.
"""

import asyncio
from flask import Blueprint, jsonify, request
from typing import Dict, Any, List

from src.api.marcus_server_singleton import get_marcus_server
from src.api.async_wrapper import async_route

# Create blueprint
context_api = Blueprint('context_api', __name__, url_prefix='/api/context')


@context_api.route('/health', methods=['GET'])
def health():
    """Health check for context API."""
    return jsonify({
        "status": "healthy",
        "service": "context-visualization-api"
    })


@context_api.route('/task/<task_id>', methods=['GET'])
@async_route
async def get_task_context(task_id: str):
    """
    Get context information for a specific task.
    
    Returns:
        - Previous implementations from dependencies
        - Tasks that depend on this one
        - Related architectural decisions
        - Relevant patterns
    """
    try:
        server = await get_marcus_server()
        
        if not server.context:
            return jsonify({
                "error": "Context system not enabled",
                "hint": "Enable 'context' in features configuration"
            }), 503
            
        # Get task details first
        task = None
        for t in server.project_tasks:
            if t.id == task_id:
                task = t
                break
                
        if not task:
            return jsonify({"error": f"Task {task_id} not found"}), 404
            
        # Get context
        context = await server.context.get_context(
            task_id, 
            task.dependencies or []
        )
        
        # Format for visualization
        viz_data = {
            "task": {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "status": task.status.value,
                "labels": task.labels,
                "dependencies": task.dependencies or []
            },
            "context": context.to_dict(),
            "visualization": {
                "dependency_graph": _create_dependency_graph(task, context),
                "implementation_timeline": _create_implementation_timeline(context),
                "decision_impact": _analyze_decision_impact(context)
            }
        }
        
        return jsonify(viz_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@context_api.route('/dependencies', methods=['GET'])
@async_route
async def get_dependencies():
    """
    Get dependency graph for all tasks in the current project.
    
    Query params:
        - infer: Whether to infer implicit dependencies (default: true)
    """
    try:
        server = await get_marcus_server()
        
        if not server.context:
            return jsonify({
                "error": "Context system not enabled"
            }), 503
            
        # Get inference preference
        infer = request.args.get('infer', 'true').lower() == 'true'
        
        # Analyze dependencies
        dep_map = server.context.analyze_dependencies(
            server.project_tasks,
            infer_implicit=infer
        )
        
        # Check for circular dependencies
        cycles = server.context._detect_circular_dependencies(
            dep_map, 
            server.project_tasks
        )
        
        # Suggest optimal order
        suggested_order = server.context.suggest_task_order(server.project_tasks)
        
        # Format for visualization
        nodes = []
        edges = []
        
        # Create nodes for all tasks
        task_lookup = {t.id: t for t in server.project_tasks}
        for task in server.project_tasks:
            nodes.append({
                "id": task.id,
                "label": task.name,
                "status": task.status.value,
                "priority": task.priority.value,
                "group": task.labels[0] if task.labels else "general"
            })
            
        # Create edges for dependencies
        for source_id, dependent_ids in dep_map.items():
            for target_id in dependent_ids:
                edges.append({
                    "from": source_id,
                    "to": target_id,
                    "label": "depends on",
                    "inferred": _is_inferred_dependency(source_id, target_id, task_lookup)
                })
                
        return jsonify({
            "graph": {
                "nodes": nodes,
                "edges": edges
            },
            "statistics": {
                "total_tasks": len(server.project_tasks),
                "total_dependencies": sum(len(deps) for deps in dep_map.values()),
                "circular_dependencies": len(cycles),
                "inferred_dependencies": len([e for e in edges if e.get("inferred")])
            },
            "issues": {
                "circular_dependencies": cycles
            },
            "suggested_order": [
                {"id": t.id, "name": t.name} for t in suggested_order
            ]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@context_api.route('/decisions', methods=['GET'])
@async_route
async def get_decisions():
    """Get all architectural decisions made in the project."""
    try:
        server = await get_marcus_server()
        
        if not server.context:
            return jsonify({
                "error": "Context system not enabled"
            }), 503
            
        # Get all decisions
        decisions = []
        for decision in server.context.decisions:
            decisions.append({
                "id": decision.id,
                "task_id": decision.task_id,
                "agent_id": decision.agent_id,
                "timestamp": decision.timestamp.isoformat(),
                "what": decision.what,
                "why": decision.why,
                "impact": decision.impact
            })
            
        # Group by task
        by_task = {}
        for decision in decisions:
            task_id = decision["task_id"]
            if task_id not in by_task:
                by_task[task_id] = []
            by_task[task_id].append(decision)
            
        return jsonify({
            "decisions": decisions,
            "by_task": by_task,
            "total": len(decisions)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@context_api.route('/implementations', methods=['GET'])
@async_route
async def get_implementations():
    """Get all tracked implementations."""
    try:
        server = await get_marcus_server()
        
        if not server.context:
            return jsonify({
                "error": "Context system not enabled"
            }), 503
            
        implementations = []
        for task_id, impl in server.context.implementations.items():
            implementations.append({
                "task_id": task_id,
                "implementation": impl,
                "summary": _summarize_implementation(impl)
            })
            
        return jsonify({
            "implementations": implementations,
            "total": len(implementations)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@context_api.route('/patterns', methods=['GET'])
@async_route
async def get_patterns():
    """Get identified patterns from implementations."""
    try:
        server = await get_marcus_server()
        
        if not server.context:
            return jsonify({
                "error": "Context system not enabled"
            }), 503
            
        return jsonify({
            "patterns": server.context.patterns,
            "pattern_types": list(server.context.patterns.keys())
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Helper functions

def _create_dependency_graph(task, context) -> Dict[str, Any]:
    """Create visualization data for dependency graph."""
    nodes = [{"id": task.id, "label": task.name, "type": "current"}]
    edges = []
    
    # Add dependency nodes
    for dep_id, impl in context.previous_implementations.items():
        nodes.append({
            "id": dep_id,
            "label": f"Task {dep_id}",
            "type": "dependency"
        })
        edges.append({
            "from": dep_id,
            "to": task.id,
            "label": "provides"
        })
        
    # Add dependent nodes
    for dep in context.dependent_tasks:
        nodes.append({
            "id": dep["task_id"],
            "label": dep["task_name"],
            "type": "dependent"
        })
        edges.append({
            "from": task.id,
            "to": dep["task_id"],
            "label": "required by"
        })
        
    return {"nodes": nodes, "edges": edges}


def _create_implementation_timeline(context) -> List[Dict[str, Any]]:
    """Create timeline of implementations."""
    timeline = []
    
    for impl_id, impl_data in context.previous_implementations.items():
        timeline.append({
            "task_id": impl_id,
            "timestamp": impl_data.get("timestamp"),
            "type": "implementation",
            "summary": _summarize_implementation(impl_data)
        })
        
    # Sort by timestamp
    timeline.sort(key=lambda x: x.get("timestamp", ""))
    
    return timeline


def _analyze_decision_impact(context) -> Dict[str, Any]:
    """Analyze the impact of architectural decisions."""
    impact_analysis = {
        "affected_tasks": [],
        "key_decisions": [],
        "risk_areas": []
    }
    
    for decision in context.architectural_decisions:
        # Identify high-impact decisions
        if "all" in decision.impact.lower() or "every" in decision.impact.lower():
            impact_analysis["key_decisions"].append({
                "what": decision.what,
                "impact": decision.impact
            })
            
        # Identify risk areas
        if any(word in decision.why.lower() for word in ["concern", "risk", "issue"]):
            impact_analysis["risk_areas"].append({
                "decision": decision.what,
                "reason": decision.why
            })
            
    return impact_analysis


def _summarize_implementation(impl_data: Dict[str, Any]) -> str:
    """Create a summary of implementation details."""
    summary_parts = []
    
    if "apis" in impl_data:
        summary_parts.append(f"{len(impl_data['apis'])} APIs")
    if "endpoints" in impl_data:
        summary_parts.append(f"{len(impl_data['endpoints'])} endpoints")
    if "models" in impl_data:
        summary_parts.append(f"{len(impl_data['models'])} models")
    if "schema" in impl_data:
        summary_parts.append(f"{len(impl_data['schema'])} tables")
    if "patterns" in impl_data:
        summary_parts.append(f"{len(impl_data['patterns'])} patterns")
        
    return ", ".join(summary_parts) if summary_parts else "Implementation details"


def _is_inferred_dependency(source_id: str, target_id: str, task_lookup: dict) -> bool:
    """Check if a dependency was inferred rather than explicit."""
    source_task = task_lookup.get(source_id)
    if source_task and source_task.dependencies:
        return target_id not in source_task.dependencies
    return True