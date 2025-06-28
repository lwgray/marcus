"""
Context Detection for Marcus Hybrid Approach

Determines which Marcus mode would be most helpful based on board state,
user interactions, and explicit preferences.
"""

import logging
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from src.detection.board_analyzer import BoardAnalyzer, BoardState
from src.core.models import Task

logger = logging.getLogger(__name__)


class MarcusMode(Enum):
    """Available Marcus operating modes"""
    CREATOR = "creator"      # Generate project structure from requirements
    ENRICHER = "enricher"    # Add metadata and organization to existing tasks
    ADAPTIVE = "adaptive"    # Coordinate within existing structure


class UserIntent(Enum):
    """Detected user intents from messages"""
    CREATE = "create"        # Want to create new project/tasks
    ORGANIZE = "organize"    # Want to organize existing tasks
    COORDINATE = "coordinate"  # Want task assignment/coordination
    QUERY = "query"          # Just asking questions
    UNKNOWN = "unknown"


@dataclass
class ModeRecommendation:
    """Recommendation for which mode to use"""
    recommended_mode: MarcusMode
    confidence: float
    reasoning: str
    alternative_modes: List[MarcusMode]


@dataclass
class UserContext:
    """Context about the user's recent interactions"""
    recent_messages: List[str]
    last_mode_switch: Optional[datetime]
    mode_preferences: Dict[MarcusMode, int]  # Usage counts
    current_mode: Optional[MarcusMode]


class ContextDetector:
    """Determines which Marcus mode would be most helpful"""
    
    # Intent patterns for parsing user messages
    INTENT_PATTERNS = {
        UserIntent.CREATE: [
            r"create.*project",
            r"new.*project",
            r"start.*from.*scratch",
            r"generate.*tasks",
            r"from.*prd",
            r"build.*mvp",
            r"need.*structure",
            r"empty.*board"
        ],
        UserIntent.ORGANIZE: [
            r"organize",
            r"structure",
            r"clean.*up",
            r"add.*metadata",
            r"enrich",
            r"improve.*board",
            r"mess",
            r"chaotic"
        ],
        UserIntent.COORDINATE: [
            r"assign",
            r"next.*task",
            r"who.*should",
            r"coordinate",
            r"ready.*for.*work",
            r"what.*should.*work"
        ]
    }
    
    def __init__(self, board_analyzer: BoardAnalyzer):
        self.board_analyzer = board_analyzer
        self.user_contexts: Dict[str, UserContext] = {}
    
    async def detect_optimal_mode(
        self, 
        user_id: str,
        board_id: str,
        tasks: List[Task],
        recent_message: Optional[str] = None
    ) -> ModeRecommendation:
        """
        Decision tree for mode selection:
        1. Check board state
        2. Check recent user interactions
        3. Check explicit preferences
        4. Make recommendation
        
        Args:
            user_id: User making the request
            board_id: Board to analyze
            tasks: Current tasks on the board
            recent_message: Most recent user message (if any)
            
        Returns:
            Mode recommendation with confidence
        """
        # Get or create user context
        user_context = self._get_user_context(user_id)
        
        # Add recent message if provided
        if recent_message:
            user_context.recent_messages.append(recent_message)
            # Keep only last 10 messages
            user_context.recent_messages = user_context.recent_messages[-10:]
        
        # Analyze board state
        board_state = await self.board_analyzer.analyze_board(board_id, tasks)
        
        # Detect user intent from recent messages
        user_intent = UserIntent.UNKNOWN
        if recent_message:
            user_intent = await self.detect_user_intent(recent_message)
        
        # Make recommendation based on all factors
        recommendation = self._make_recommendation(
            board_state=board_state,
            user_intent=user_intent,
            user_context=user_context
        )
        
        return recommendation
    
    async def detect_user_intent(self, message: str) -> UserIntent:
        """
        Parse user messages for intent
        
        Args:
            message: User's message
            
        Returns:
            Detected intent
        """
        message_lower = message.lower()
        
        # Check each intent pattern
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    logger.info(f"Detected intent {intent} from pattern '{pattern}'")
                    return intent
                    
        return UserIntent.UNKNOWN
    
    def _make_recommendation(
        self,
        board_state: BoardState,
        user_intent: UserIntent,
        user_context: UserContext
    ) -> ModeRecommendation:
        """
        Make mode recommendation based on all factors
        
        Priority order:
        1. Explicit user intent (if clear)
        2. Board state recommendation
        3. User preferences/history
        """
        # Handle explicit user intent
        if user_intent != UserIntent.UNKNOWN:
            intent_recommendation = self._recommend_from_intent(user_intent)
            if intent_recommendation:
                return intent_recommendation
        
        # Handle empty board
        if board_state.is_empty:
            return ModeRecommendation(
                recommended_mode=MarcusMode.CREATOR,
                confidence=0.95,
                reasoning="Empty board detected - Creator mode can help structure your project",
                alternative_modes=[MarcusMode.ADAPTIVE]
            )
        
        # Handle chaotic board
        if board_state.is_chaotic:
            return ModeRecommendation(
                recommended_mode=MarcusMode.ENRICHER,
                confidence=0.85,
                reasoning=f"Board has {board_state.task_count} tasks but low structure score ({board_state.structure_score:.2f}) - Enricher mode can help organize",
                alternative_modes=[MarcusMode.ADAPTIVE, MarcusMode.CREATOR]
            )
        
        # Handle well-structured board
        if board_state.is_well_structured:
            return ModeRecommendation(
                recommended_mode=MarcusMode.ADAPTIVE,
                confidence=0.90,
                reasoning=f"Board is well-structured (score: {board_state.structure_score:.2f}) - Adaptive mode can coordinate work efficiently",
                alternative_modes=[MarcusMode.ENRICHER]
            )
        
        # Default recommendation based on board state
        mode_map = {
            "creator": MarcusMode.CREATOR,
            "enricher": MarcusMode.ENRICHER,
            "adaptive": MarcusMode.ADAPTIVE
        }
        
        recommended = mode_map.get(board_state.recommended_mode, MarcusMode.ADAPTIVE)
        
        return ModeRecommendation(
            recommended_mode=recommended,
            confidence=0.70,
            reasoning=f"Based on board analysis: {board_state.task_count} tasks with {board_state.metadata_completeness:.0%} metadata completeness",
            alternative_modes=self._get_alternative_modes(recommended)
        )
    
    def _recommend_from_intent(self, intent: UserIntent) -> Optional[ModeRecommendation]:
        """Get mode recommendation from user intent"""
        intent_mode_map = {
            UserIntent.CREATE: ModeRecommendation(
                recommended_mode=MarcusMode.CREATOR,
                confidence=0.90,
                reasoning="You want to create a new project structure",
                alternative_modes=[MarcusMode.ENRICHER]
            ),
            UserIntent.ORGANIZE: ModeRecommendation(
                recommended_mode=MarcusMode.ENRICHER,
                confidence=0.90,
                reasoning="You want to organize and enrich existing tasks",
                alternative_modes=[MarcusMode.ADAPTIVE]
            ),
            UserIntent.COORDINATE: ModeRecommendation(
                recommended_mode=MarcusMode.ADAPTIVE,
                confidence=0.90,
                reasoning="You want to coordinate task assignments",
                alternative_modes=[MarcusMode.ENRICHER]
            )
        }
        
        return intent_mode_map.get(intent)
    
    def _get_alternative_modes(self, recommended: MarcusMode) -> List[MarcusMode]:
        """Get alternative modes for a recommendation"""
        alternatives = {
            MarcusMode.CREATOR: [MarcusMode.ENRICHER, MarcusMode.ADAPTIVE],
            MarcusMode.ENRICHER: [MarcusMode.ADAPTIVE, MarcusMode.CREATOR],
            MarcusMode.ADAPTIVE: [MarcusMode.ENRICHER, MarcusMode.CREATOR]
        }
        
        return alternatives.get(recommended, [])[0:2]  # Return top 2 alternatives
    
    def _get_user_context(self, user_id: str) -> UserContext:
        """Get or create user context"""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = UserContext(
                recent_messages=[],
                last_mode_switch=None,
                mode_preferences={
                    MarcusMode.CREATOR: 0,
                    MarcusMode.ENRICHER: 0,
                    MarcusMode.ADAPTIVE: 0
                },
                current_mode=None
            )
            
        return self.user_contexts[user_id]
    
    def record_mode_switch(self, user_id: str, new_mode: MarcusMode):
        """Record when a user switches modes"""
        context = self._get_user_context(user_id)
        context.last_mode_switch = datetime.now()
        context.current_mode = new_mode
        context.mode_preferences[new_mode] += 1
    
    def get_mode_suggestions(self, board_state: BoardState) -> List[str]:
        """Get helpful suggestions based on board state"""
        suggestions = []
        
        if board_state.is_empty:
            suggestions.append("🎯 Try Creator mode to generate a project structure from requirements")
            suggestions.append("📝 Describe your project and I'll help create tasks")
            
        elif board_state.is_chaotic:
            suggestions.append("🔧 Try Enricher mode to add structure to your tasks")
            suggestions.append("🏷️ I can help add labels, estimates, and dependencies")
            
        elif board_state.task_count < 10:
            suggestions.append("➕ Your board might be missing tasks - Creator mode can help")
            
        elif board_state.metadata_completeness < 0.5:
            suggestions.append("📊 Many tasks lack metadata - Enricher mode can help")
            
        else:
            suggestions.append("✅ Your board looks well-organized!")
            suggestions.append("🤖 Adaptive mode can help coordinate work")
            
        return suggestions