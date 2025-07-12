"""
Decision visualization component for Marcus

Visualizes Marcus's decision-making process including:
- Decision trees
- Alternative paths considered
- Confidence scores
- Decision factors
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
from pyvis.network import Network


@dataclass
class Decision:
    """Represents a single decision made by Marcus"""

    id: str
    timestamp: datetime
    decision: str
    rationale: str
    confidence_score: float
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    decision_factors: Dict[str, Any] = field(default_factory=dict)
    outcome: Optional[str] = None
    outcome_timestamp: Optional[datetime] = None

    def was_successful(self) -> Optional[bool]:
        """Determine if decision was successful based on outcome"""
        if not self.outcome:
            return None
        # Simple heuristic - can be made more sophisticated
        success_indicators = ["completed", "success", "resolved", "assigned"]
        failure_indicators = ["failed", "blocked", "error", "timeout"]

        outcome_lower = self.outcome.lower()
        if any(indicator in outcome_lower for indicator in success_indicators):
            return True
        elif any(indicator in outcome_lower for indicator in failure_indicators):
            return False
        return None


@dataclass
class DecisionNode:
    """Node in decision tree visualization"""

    id: str
    label: str
    node_type: str  # 'decision', 'alternative', 'factor', 'outcome'
    value: Any
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DecisionVisualizer:
    """
    Visualizes Marcus's decision-making process
    """

    def __init__(self) -> None:
        self.decisions: Dict[str, Decision] = {}
        self.decision_graph = nx.DiGraph()
        self.decision_patterns: Dict[str, List[Decision]] = defaultdict(list)

    def add_decision(self, decision_data: Dict[str, Any]) -> str:
        """Add a new decision to track"""
        decision_id = decision_data.get("id", f"decision_{len(self.decisions)}")

        decision = Decision(
            id=decision_id,
            timestamp=datetime.fromisoformat(decision_data["timestamp"]),
            decision=decision_data["decision"],
            rationale=decision_data["rationale"],
            confidence_score=decision_data.get("confidence_score", 0.5),
            alternatives=decision_data.get("alternatives_considered", []),
            decision_factors=decision_data.get("decision_factors", {}),
        )

        self.decisions[decision_id] = decision
        self._update_decision_graph(decision)
        self._analyze_pattern(decision)

        return decision_id

    def update_decision_outcome(self, decision_id: str, outcome: str) -> None:
        """Update the outcome of a decision"""
        if decision_id in self.decisions:
            self.decisions[decision_id].outcome = outcome
            self.decisions[decision_id].outcome_timestamp = datetime.now()

    def _update_decision_graph(self, decision: Decision) -> None:
        """Update the decision graph with new decision"""
        # Add main decision node
        decision_node_id = f"decision_{decision.id}"
        self.decision_graph.add_node(
            decision_node_id,
            label=(
                decision.decision[:50] + "..."
                if len(decision.decision) > 50
                else decision.decision
            ),
            node_type="decision",
            confidence=decision.confidence_score,
            timestamp=decision.timestamp.isoformat(),
        )

        # Add rationale node
        rationale_node_id = f"rationale_{decision.id}"
        self.decision_graph.add_node(
            rationale_node_id,
            label=(
                decision.rationale[:50] + "..."
                if len(decision.rationale) > 50
                else decision.rationale
            ),
            node_type="rationale",
        )
        self.decision_graph.add_edge(decision_node_id, rationale_node_id)

        # Add alternative nodes
        for i, alt in enumerate(decision.alternatives):
            alt_node_id = f"alt_{decision.id}_{i}"
            self.decision_graph.add_node(
                alt_node_id,
                label=str(alt.get("task", alt))[:30] + "...",
                node_type="alternative",
                score=alt.get("score", 0),
            )
            self.decision_graph.add_edge(decision_node_id, alt_node_id, weight=0.5)

        # Add decision factor nodes
        for factor, value in decision.decision_factors.items():
            factor_node_id = f"factor_{decision.id}_{factor}"
            self.decision_graph.add_node(
                factor_node_id,
                label=f"{factor}: {value}",
                node_type="factor",
                value=value,
            )
            self.decision_graph.add_edge(rationale_node_id, factor_node_id)

    def _analyze_pattern(self, decision: Decision) -> None:
        """Analyze decision for patterns"""
        # Extract decision type (e.g., task assignment, blocker resolution)
        decision_type = self._classify_decision(decision.decision)
        self.decision_patterns[decision_type].append(decision)

    def _classify_decision(self, decision_text: str) -> str:
        """Classify decision into categories"""
        decision_lower = decision_text.lower()

        if "assign" in decision_lower and "task" in decision_lower:
            return "task_assignment"
        elif "blocker" in decision_lower or "resolution" in decision_lower:
            return "blocker_resolution"
        elif "priorit" in decision_lower:
            return "prioritization"
        elif "escalate" in decision_lower:
            return "escalation"
        else:
            return "other"

    def generate_decision_tree_html(
        self, decision_id: str, output_file: str = "decision_tree.html"
    ) -> Optional[str]:
        """Generate interactive HTML visualization of a decision tree"""
        if decision_id not in self.decisions:
            return None

        # Create subgraph for this decision
        decision_nodes = [n for n in self.decision_graph.nodes() if decision_id in n]
        subgraph = self.decision_graph.subgraph(decision_nodes)

        # Create Pyvis network
        net = Network(height="750px", width="100%", directed=True)
        net.from_nx(subgraph)

        # Customize node appearance based on type
        for node in net.nodes:
            node_data = self.decision_graph.nodes[node["id"]]
            node_type = node_data.get("node_type", "default")

            if node_type == "decision":
                node["color"] = "#3498db"
                node["size"] = 30
            elif node_type == "rationale":
                node["color"] = "#9b59b6"
                node["size"] = 20
            elif node_type == "alternative":
                node["color"] = "#e74c3c"
                node["size"] = 15
            elif node_type == "factor":
                node["color"] = "#2ecc71"
                node["size"] = 15

        # Set physics options for better layout
        net.set_options(
            """
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -8000,
              "springConstant": 0.04,
              "damping": 0.09
            }
          }
        }
        """
        )

        net.save_graph(output_file)
        return output_file

    def get_decision_analytics(self) -> Dict[str, Any]:
        """Get analytics on decision-making patterns"""
        analytics: Dict[str, Any] = {
            "total_decisions": len(self.decisions),
            "average_confidence": 0,
            "decision_types": {},
            "success_rate": 0,
            "average_alternatives_considered": 0,
            "most_common_factors": {},
            "decision_time_distribution": [],
        }

        if not self.decisions:
            return analytics

        # Calculate metrics
        total_confidence = 0.0
        successful_decisions = 0
        total_alternatives = 0
        factor_counts: Dict[str, int] = defaultdict(int)

        for decision in self.decisions.values():
            total_confidence += decision.confidence_score
            total_alternatives += len(decision.alternatives)

            # Count successful decisions
            if decision.was_successful():
                successful_decisions += 1

            # Count decision factors
            for factor in decision.decision_factors:
                factor_counts[factor] += 1

            # Track time of day
            hour = decision.timestamp.hour
            analytics["decision_time_distribution"].append(hour)

        # Calculate averages
        analytics["average_confidence"] = total_confidence / len(self.decisions)
        analytics["success_rate"] = (
            successful_decisions / len(self.decisions) if self.decisions else 0
        )
        analytics["average_alternatives_considered"] = total_alternatives / len(
            self.decisions
        )

        # Decision type distribution
        for pattern_type, decisions in self.decision_patterns.items():
            analytics["decision_types"][pattern_type] = len(decisions)

        # Most common factors
        analytics["most_common_factors"] = dict(
            sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        return analytics

    def get_confidence_trends(self) -> List[Tuple[datetime, float]]:
        """Get confidence scores over time"""
        trends = []
        for decision in sorted(self.decisions.values(), key=lambda d: d.timestamp):
            trends.append((decision.timestamp, decision.confidence_score))
        return trends

    def find_similar_decisions(
        self, decision_id: str, threshold: float = 0.7
    ) -> List[str]:
        """Find decisions similar to the given one"""
        if decision_id not in self.decisions:
            return []

        target_decision = self.decisions[decision_id]
        similar = []

        for other_id, other_decision in self.decisions.items():
            if other_id == decision_id:
                continue

            # Calculate similarity based on factors and decision type
            similarity = self._calculate_decision_similarity(
                target_decision, other_decision
            )
            if similarity >= threshold:
                similar.append((other_id, similarity))

        # Sort by similarity
        similar.sort(key=lambda x: x[1], reverse=True)
        return [decision_id for decision_id, _ in similar]

    def _calculate_decision_similarity(
        self, decision1: Decision, decision2: Decision
    ) -> float:
        """Calculate similarity between two decisions"""
        # Simple similarity based on shared factors
        factors1 = set(decision1.decision_factors.keys())
        factors2 = set(decision2.decision_factors.keys())

        if not factors1 and not factors2:
            return 0.0

        intersection = factors1.intersection(factors2)
        union = factors1.union(factors2)

        return len(intersection) / len(union) if union else 0.0

    def export_decision_data(self, format: str = "json") -> str:
        """Export decision data for external analysis"""
        export_data: Dict[str, Any] = {
            "decisions": [],
            "patterns": {},
            "analytics": self.get_decision_analytics(),
        }

        # Convert decisions to serializable format
        for decision in self.decisions.values():
            export_data["decisions"].append(
                {
                    "id": decision.id,
                    "timestamp": decision.timestamp.isoformat(),
                    "decision": decision.decision,
                    "rationale": decision.rationale,
                    "confidence_score": decision.confidence_score,
                    "alternatives": decision.alternatives,
                    "decision_factors": decision.decision_factors,
                    "outcome": decision.outcome,
                    "was_successful": decision.was_successful(),
                }
            )

        # Add pattern data
        for pattern_type, decisions in self.decision_patterns.items():
            export_data["patterns"][pattern_type] = len(decisions)

        if format == "json":
            return json.dumps(export_data, indent=2)
        else:
            # Could add other formats (CSV, etc.)
            return json.dumps(export_data)
