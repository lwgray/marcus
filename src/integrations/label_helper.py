#!/usr/bin/env python3
"""
Helper module for managing labels in kanban-mcp.

This module provides utility functions for working with labels, handling the
specific requirements of the kanban-mcp label manager including:
- Using proper color names from the allowed enum
- Creating labels before adding them to cards
- Managing label IDs for card operations
"""

import json
from typing import Any, Dict, List, Optional


class LabelManagerHelper:
    """Helper class for managing kanban labels."""

    # Valid colors from kanban-mcp schema
    VALID_COLORS = [
        "berry-red",
        "pumpkin-orange",
        "lagoon-blue",
        "pink-tulip",
        "light-mud",
        "orange-peel",
        "bright-moss",
        "antique-blue",
        "dark-granite",
        "lagune-blue",
        "sunny-grass",
        "morning-sky",
        "light-orange",
        "midnight-blue",
        "tank-green",
        "gun-metal",
        "wet-moss",
        "red-burgundy",
        "light-concrete",
        "apricot-red",
        "desert-sand",
        "navy-blue",
        "egg-yellow",
        "coral-green",
        "light-cocoa",
    ]

    # Mapping of common label names to appropriate colors
    DEFAULT_LABEL_COLORS = {
        # Skills/Technologies
        "backend": "berry-red",
        "frontend": "lagoon-blue",
        "database": "pumpkin-orange",
        "api": "berry-red",
        "ui": "lagune-blue",
        "ux": "lagune-blue",
        "devops": "tank-green",
        "fullstack": "midnight-blue",
        "react": "lagoon-blue",
        "django": "bright-moss",
        "python": "bright-moss",
        "nodejs": "sunny-grass",
        "javascript": "egg-yellow",
        # Task types
        "testing": "sunny-grass",
        "bug": "midnight-blue",
        "feature": "pink-tulip",
        "documentation": "sunny-grass",
        "refactor": "light-concrete",
        "enhancement": "bright-moss",
        "setup": "pink-tulip",
        "deployment": "pumpkin-orange",
        "design": "lagune-blue",
        "implementation": "berry-red",
        # Priorities
        "high": "berry-red",
        "medium": "egg-yellow",
        "low": "bright-moss",
        "urgent": "red-burgundy",
        "high-priority": "red-burgundy",
        # Complexity
        "simple": "bright-moss",
        "moderate": "egg-yellow",
        "complex": "berry-red",
        # Other
        "security": "midnight-blue",
        "performance": "orange-peel",
        "authentication": "midnight-blue",
        "infrastructure": "tank-green",
    }

    def __init__(self, session: Any, board_id: str) -> None:
        """
        Initialize the label manager helper.

        Parameters
        ----------
        session : ClientSession
            Active MCP client session
        board_id : str
            ID of the board to manage labels for
        """
        self.session = session
        self.board_id = board_id
        self._label_cache: Dict[str, Any] = {}  # Cache of label name -> label data

    async def refresh_labels(self) -> List[Dict[str, Any]]:
        """
        Get all labels for the board and refresh the cache.

        Returns
        -------
        List[Dict[str, Any]]
            List of all labels on the board
        """
        result = await self.session.call_tool(
            "mcp_kanban_label_manager", {"action": "get_all", "boardId": self.board_id}
        )

        labels = []
        if result and hasattr(result, "content") and result.content:
            labels_data = json.loads(result.content[0].text)
            labels = labels_data if isinstance(labels_data, list) else []

            # Update cache
            self._label_cache.clear()
            for label in labels:
                name = label.get("name", "").lower()
                if name:
                    self._label_cache[name] = label

        return labels

    async def ensure_label_exists(self, name: str, color: Optional[str] = None) -> str:
        """
        Ensure a label exists, creating it if necessary.

        Parameters
        ----------
        name : str
            Name of the label
        color : Optional[str]
            Color for the label. If not provided, uses default mapping or picks one.

        Returns
        -------
        str
            ID of the label (existing or newly created)

        Raises
        ------
        ValueError
            If the color is not in the valid colors list
        """
        # Normalize name
        normalized_name = name.lower()

        # Check cache first
        if normalized_name in self._label_cache:
            cached_label = self._label_cache[normalized_name]
            # Verify the color is correct
            expected_color = self.get_color_for_label(name)
            if cached_label["color"] != expected_color:
                # Update the label color
                print(
                    f"Updating label '{name}' color from {cached_label['color']} to {expected_color}"
                )
                try:
                    update_result = await self.session.call_tool(
                        "mcp_kanban_label_manager",
                        {
                            "action": "update",
                            "id": cached_label["id"],
                            "boardId": self.board_id,
                            "name": name,
                            "color": expected_color,
                            "position": cached_label.get("position", 65536),
                        },
                    )
                    if (
                        update_result
                        and hasattr(update_result, "content")
                        and update_result.content
                    ):
                        updated_label = json.loads(update_result.content[0].text)
                        self._label_cache[normalized_name] = updated_label
                except Exception as e:
                    print(f"Failed to update label color: {e}")
            return str(cached_label["id"])

        # Refresh cache and check again
        await self.refresh_labels()
        if normalized_name in self._label_cache:
            cached_label = self._label_cache[normalized_name]
            # Verify the color is correct
            expected_color = self.get_color_for_label(name)
            if cached_label["color"] != expected_color:
                # Update the label color
                print(
                    f"Updating label '{name}' color from {cached_label['color']} to {expected_color}"
                )
                try:
                    update_result = await self.session.call_tool(
                        "mcp_kanban_label_manager",
                        {
                            "action": "update",
                            "id": cached_label["id"],
                            "boardId": self.board_id,
                            "name": name,
                            "color": expected_color,
                            "position": cached_label.get("position", 65536),
                        },
                    )
                    if (
                        update_result
                        and hasattr(update_result, "content")
                        and update_result.content
                    ):
                        updated_label = json.loads(update_result.content[0].text)
                        self._label_cache[normalized_name] = updated_label
                except Exception as e:
                    print(f"Failed to update label color: {e}")
            return str(cached_label["id"])

        # Need to create the label
        if color is None:
            # Use the class method for consistency
            color = self.get_color_for_label(name)

        # Validate color
        if color not in self.VALID_COLORS:
            raise ValueError(
                f"Invalid color '{color}'. Must be one of: {', '.join(self.VALID_COLORS)}"
            )

        # Create the label with required position parameter
        result = await self.session.call_tool(
            "mcp_kanban_label_manager",
            {
                "action": "create",
                "boardId": self.board_id,
                "name": name,  # Use original name (preserves case)
                "color": color,
                "position": 65536,  # Required parameter for label creation
            },
        )

        if result and hasattr(result, "content") and result.content:
            created_label = json.loads(result.content[0].text)
            # Update cache
            self._label_cache[normalized_name] = created_label
            return str(created_label["id"])
        else:
            raise Exception(f"Failed to create label '{name}'")

    async def add_labels_to_card(
        self, card_id: str, label_names: List[str]
    ) -> List[str]:
        """
        Add multiple labels to a card, creating them if necessary.

        Parameters
        ----------
        card_id : str
            ID of the card to add labels to
        label_names : List[str]
            Names of labels to add

        Returns
        -------
        List[str]
            List of label IDs that were successfully added
        """
        added_label_ids = []

        for label_name in label_names:
            try:
                # Ensure label exists and get its ID
                label_id = await self.ensure_label_exists(label_name)

                # Add label to card
                await self.session.call_tool(
                    "mcp_kanban_label_manager",
                    {"action": "add_to_card", "cardId": card_id, "labelId": label_id},
                )

                added_label_ids.append(label_id)

            except Exception as e:
                print(f"Warning: Failed to add label '{label_name}' to card: {e}")

        return added_label_ids

    @classmethod
    def get_color_for_label(cls, label_name: str) -> str:
        """
        Get the recommended color for a label name.

        Parameters
        ----------
        label_name : str
            Name of the label

        Returns
        -------
        str
            Recommended color from the valid colors list
        """
        normalized = label_name.lower()

        # Handle prefixed labels (e.g., "component:frontend" -> check "frontend")
        if ":" in normalized:
            prefix, suffix = normalized.split(":", 1)

            # Try exact suffix match first
            color = cls.DEFAULT_LABEL_COLORS.get(suffix, None)

            # If not found, try to find a matching key in suffix (e.g., "python" in "python-255887")
            if not color:
                for key in cls.DEFAULT_LABEL_COLORS:
                    if key in suffix:
                        color = cls.DEFAULT_LABEL_COLORS[key]
                        break

            # If not found, try prefix
            if not color:
                color = cls.DEFAULT_LABEL_COLORS.get(prefix, None)

            # If still not found, use a color based on prefix type
            if not color:
                prefix_colors = {
                    "component": "bright-moss",
                    "type": "pumpkin-orange",
                    "priority": "berry-red",
                    "skill": "lagoon-blue",
                    "complexity": "light-concrete",
                }
                color = prefix_colors.get(prefix, "lagoon-blue")
            return color
        else:
            # Simple label without prefix
            return cls.DEFAULT_LABEL_COLORS.get(normalized, "lagoon-blue")

    @classmethod
    def map_hex_to_valid_color(cls, hex_color: str) -> str:
        """
        Map a hex color to the closest valid kanban-mcp color.

        This is a simple mapping for common colors.

        Parameters
        ----------
        hex_color : str
            Hex color code (e.g., "#4CAF50")

        Returns
        -------
        str
            Valid color name from the allowed list
        """
        hex_mappings = {
            "#4CAF50": "sunny-grass",  # Green
            "#2196F3": "lagoon-blue",  # Blue
            "#FF9800": "pumpkin-orange",  # Orange
            "#9C27B0": "pink-tulip",  # Purple
            "#F44336": "berry-red",  # Red
            "#795548": "light-mud",  # Brown
            "#607D8B": "dark-granite",  # Blue Grey
            "#FFEB3B": "egg-yellow",  # Yellow
            "#00BCD4": "lagune-blue",  # Cyan
            "#E91E63": "pink-tulip",  # Pink
        }

        return hex_mappings.get(hex_color.upper(), "lagoon-blue")


# Example usage function
async def example_usage(session: Any, board_id: str, card_id: str) -> None:
    """
    Example of how to use the LabelManagerHelper.

    Parameters
    ----------
    session : ClientSession
        Active MCP session
    board_id : str
        Board ID
    card_id : str
        Card ID to add labels to
    """
    # Create helper
    helper = LabelManagerHelper(session, board_id)

    # Add labels to a card (creates them if they don't exist)
    labels_to_add = ["backend", "python", "high-priority"]
    added_ids = await helper.add_labels_to_card(card_id, labels_to_add)
    print(f"Added {len(added_ids)} labels to card")

    # Get all labels on the board
    all_labels = await helper.refresh_labels()
    print(f"Board has {len(all_labels)} total labels")

    # Get color for a label type
    color = LabelManagerHelper.get_color_for_label("frontend")
    print(f"Recommended color for 'frontend': {color}")
