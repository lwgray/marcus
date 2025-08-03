"""
Card loader module for loading card data from JSON.

This module provides functions to load and manage card data.
"""

import json
import os
from typing import Dict, List, Any, Optional


def load_card_data() -> Dict[str, Any]:
    """Load card data from the JSON file."""
    json_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "todo_app_planka_cards.json"
    )
    
    with open(json_path, "r") as f:
        return json.load(f)


def get_card_by_id(card_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific card by its ID."""
    data = load_card_data()
    for card in data.get("cards", []):
        if card.get("id") == card_id:
            return card
    return None


def get_all_cards() -> List[Dict[str, Any]]:
    """Get all cards from the JSON file."""
    data = load_card_data()
    return data.get("cards", [])


def get_cards_by_category(category: str) -> List[Dict[str, Any]]:
    """Get cards filtered by category label."""
    cards = get_all_cards()
    return [
        card for card in cards
        if category in card.get("labels", [])
    ]