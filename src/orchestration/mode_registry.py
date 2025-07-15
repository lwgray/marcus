"""
Mode Registry for Marcus Hybrid Approach

Manages available Marcus modes and handles mode switching.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.detection.context_detector import MarcusMode

logger = logging.getLogger(__name__)


@dataclass
class ModeSwitch:
    """Record of a mode switch"""

    from_mode: Optional[MarcusMode]
    to_mode: MarcusMode
    timestamp: datetime
    reason: Optional[str]
    user_id: Optional[str]


class ModeRegistry:
    """Registry of available Marcus modes"""

    def __init__(self):
        """Initialize the mode registry"""
        # Import modes here to avoid circular imports
        from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode
        from src.modes.creator.basic_creator import BasicCreatorMode

        self.modes = {
            MarcusMode.CREATOR: BasicCreatorMode(),
            MarcusMode.ENRICHER: None,  # Phase 2
            MarcusMode.ADAPTIVE: BasicAdaptiveMode(),
        }
        self.current_mode = MarcusMode.ADAPTIVE  # Default mode
        self.mode_history: List[ModeSwitch] = []
        self.mode_state: Dict[MarcusMode, Dict[str, Any]] = {
            mode: {} for mode in MarcusMode
        }

        logger.info(
            f"Mode registry initialized with default mode: {self.current_mode.value}"
        )

    async def switch_mode(
        self, mode: MarcusMode, reason: str = None, user_id: str = None
    ) -> Dict[str, Any]:
        """
        Switch Marcus to a different operating mode

        Args:
            mode: Target mode to switch to
            reason: Optional reason for the switch
            user_id: Optional user who triggered the switch

        Returns:
            Result of the mode switch
        """
        # Check if mode is available
        if self.modes.get(mode) is None:
            return {
                "success": False,
                "error": f"Mode {mode.value} is not yet implemented",
                "current_mode": self.current_mode.value,
            }

        # Save current mode state
        if self.current_mode and self.current_mode in self.modes:
            current_handler = self.modes[self.current_mode]
            if current_handler and hasattr(current_handler, "get_state"):
                self.mode_state[self.current_mode] = await current_handler.get_state()

        # Record the switch
        switch = ModeSwitch(
            from_mode=self.current_mode,
            to_mode=mode,
            timestamp=datetime.now(),
            reason=reason,
            user_id=user_id,
        )
        self.mode_history.append(switch)

        # Perform the switch
        previous_mode = self.current_mode
        self.current_mode = mode

        # Initialize new mode with saved state if available
        new_handler = self.modes[mode]
        if new_handler and hasattr(new_handler, "initialize"):
            saved_state = self.mode_state.get(mode, {})
            await new_handler.initialize(saved_state)

        logger.info(
            f"Switched from {previous_mode.value} to {mode.value} mode. Reason: {reason}"
        )

        return {
            "success": True,
            "previous_mode": previous_mode.value,
            "current_mode": mode.value,
            "reason": reason,
            "message": f"Successfully switched to {mode.value} mode",
        }

    async def get_current_mode(self) -> Dict[str, Any]:
        """
        Get the currently active mode and its capabilities

        Returns:
            Information about the current mode
        """
        mode_handler = self.modes.get(self.current_mode)

        capabilities = {
            MarcusMode.CREATOR: [
                "Generate project structure from requirements",
                "Create tasks from templates",
                "Interactive project planning",
                "Automatic dependency detection",
            ],
            MarcusMode.ENRICHER: [
                "Add metadata to existing tasks",
                "Organize tasks by phase/component",
                "Infer dependencies from task content",
                "Improve task descriptions and estimates",
            ],
            MarcusMode.ADAPTIVE: [
                "Intelligent task assignment",
                "Respect existing workflow",
                "Match tasks to agent skills",
                "Simple coordination without changes",
            ],
        }

        mode_info = {
            "current_mode": self.current_mode.value,
            "description": self._get_mode_description(self.current_mode),
            "capabilities": capabilities.get(self.current_mode, []),
            "available": mode_handler is not None,
            "switch_history": len(self.mode_history),
        }

        # Add mode-specific status if available
        if mode_handler and hasattr(mode_handler, "get_status"):
            mode_info["status"] = await mode_handler.get_status()

        return mode_info

    def get_available_modes(self) -> Dict[str, bool]:
        """Get all modes and their availability"""
        return {mode.value: (self.modes.get(mode) is not None) for mode in MarcusMode}

    def get_mode_handler(self, mode: Optional[MarcusMode] = None):
        """
        Get handler for a specific mode or current mode

        Args:
            mode: Mode to get handler for (None for current)

        Returns:
            Mode handler instance or None
        """
        target_mode = mode or self.current_mode
        return self.modes.get(target_mode)

    def _get_mode_description(self, mode: MarcusMode) -> str:
        """Get human-readable description of a mode"""
        descriptions = {
            MarcusMode.CREATOR: "Create new project structures from requirements or templates",
            MarcusMode.ENRICHER: "Organize and enrich existing tasks with metadata and structure",
            MarcusMode.ADAPTIVE: "Coordinate work within your existing system without changes",
        }

        return descriptions.get(mode, "Unknown mode")

    def get_mode_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent mode switch history"""
        history = []

        for switch in reversed(self.mode_history[-limit:]):
            history.append(
                {
                    "from": switch.from_mode.value if switch.from_mode else None,
                    "to": switch.to_mode.value,
                    "timestamp": switch.timestamp.isoformat(),
                    "reason": switch.reason,
                    "user_id": switch.user_id,
                }
            )

        return history

    async def suggest_mode_switch(
        self, board_state: "BoardState", user_intent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest a mode switch based on current context

        Args:
            board_state: Current board analysis
            user_intent: Detected user intent

        Returns:
            Suggestion for mode switch or None
        """
        # Don't suggest if we just switched
        if (
            self.mode_history
            and (datetime.now() - self.mode_history[-1].timestamp).seconds < 300
        ):
            return None

        suggested_mode = None
        reason = None

        # Suggest based on board state
        if board_state.is_empty and self.current_mode != MarcusMode.CREATOR:
            suggested_mode = MarcusMode.CREATOR
            reason = (
                "Your board is empty - Creator mode can help structure your project"
            )

        elif board_state.is_chaotic and self.current_mode != MarcusMode.ENRICHER:
            if self.modes.get(MarcusMode.ENRICHER):  # Only if available
                suggested_mode = MarcusMode.ENRICHER
                reason = f"Your board has {board_state.task_count} tasks but needs organization"

        elif (
            board_state.is_well_structured and self.current_mode != MarcusMode.ADAPTIVE
        ):
            suggested_mode = MarcusMode.ADAPTIVE
            reason = "Your board is well-structured - Adaptive mode can coordinate efficiently"

        if suggested_mode:
            return {
                "suggest_switch": True,
                "from_mode": self.current_mode.value,
                "to_mode": suggested_mode.value,
                "reason": reason,
                "command": f"switch_mode(mode='{suggested_mode.value}')",
            }

        return None
