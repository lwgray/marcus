"""
Minimal stubs for pipeline replay functionality
"""

from typing import Any, Dict, List, Optional


class PipelineReplayController:
    """Minimal stub for pipeline replay"""

    def __init__(self) -> None:
        self.replay_sessions: Dict[str, Dict[str, Any]] = {}

    def start_replay(self, flow_id: str) -> Dict[str, Any]:
        """Start replay session for a flow"""
        session = {
            "flow_id": flow_id,
            "status": "active",
            "current_position": 0,
            "total_events": 0,
        }
        self.replay_sessions[flow_id] = session
        return session

    def step_forward(self, flow_id: str) -> Dict[str, Any]:
        """Step forward in replay"""
        session = self.replay_sessions.get(flow_id, {})
        if session:
            session["current_position"] = min(
                session["current_position"] + 1, session["total_events"] - 1
            )
        return session

    def step_backward(self, flow_id: str) -> Dict[str, Any]:
        """Step backward in replay"""
        session = self.replay_sessions.get(flow_id, {})
        if session:
            session["current_position"] = max(session["current_position"] - 1, 0)
        return session

    def jump_to_position(self, flow_id: str, position: int) -> Dict[str, Any]:
        """Jump to specific position"""
        session = self.replay_sessions.get(flow_id, {})
        if session:
            session["current_position"] = max(
                0, min(position, session["total_events"] - 1)
            )
        return session

    def stop_replay(self, flow_id: str) -> None:
        """Stop replay session"""
        if flow_id in self.replay_sessions:
            del self.replay_sessions[flow_id]
