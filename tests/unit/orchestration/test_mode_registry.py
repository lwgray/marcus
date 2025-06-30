"""
Unit tests for ModeRegistry

This module tests the mode registry functionality including:
- Mode registration and management
- Mode switching logic
- State preservation across mode switches
- Error handling for invalid modes
- Mode history tracking
- Mode suggestions based on board state
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

from src.orchestration.mode_registry import ModeRegistry, ModeSwitch
from src.detection.context_detector import MarcusMode
from src.detection.board_analyzer import BoardState


class TestModeRegistry:
    """Test suite for ModeRegistry functionality"""
    
    @pytest.fixture
    def mock_creator_mode(self):
        """Create mock creator mode handler"""
        mock = Mock()
        mock.get_state = AsyncMock(return_value={"creator_state": "active"})
        mock.initialize = AsyncMock()
        mock.get_status = AsyncMock(return_value={"status": "ready"})
        return mock
    
    @pytest.fixture
    def mock_adaptive_mode(self):
        """Create mock adaptive mode handler"""
        mock = Mock()
        mock.get_state = AsyncMock(return_value={"adaptive_state": "running"})
        mock.initialize = AsyncMock()
        mock.get_status = AsyncMock(return_value={"status": "operational"})
        return mock
    
    @pytest.fixture
    def mode_registry(self, mock_creator_mode, mock_adaptive_mode):
        """Create ModeRegistry instance with mocked modes"""
        with patch('src.modes.creator.basic_creator.BasicCreatorMode', return_value=mock_creator_mode):
            with patch('src.modes.adaptive.basic_adaptive.BasicAdaptiveMode', return_value=mock_adaptive_mode):
                registry = ModeRegistry()
                return registry
    
    def test_initialization(self, mode_registry):
        """Test ModeRegistry initializes with correct default state"""
        assert mode_registry.current_mode == MarcusMode.ADAPTIVE
        assert len(mode_registry.modes) == 3
        assert MarcusMode.CREATOR in mode_registry.modes
        assert MarcusMode.ADAPTIVE in mode_registry.modes
        assert MarcusMode.ENRICHER in mode_registry.modes
        assert mode_registry.modes[MarcusMode.ENRICHER] is None  # Phase 2
        assert mode_registry.mode_history == []
        assert len(mode_registry.mode_state) == 3
    
    @pytest.mark.asyncio
    async def test_switch_mode_success(self, mode_registry):
        """Test successful mode switching"""
        result = await mode_registry.switch_mode(
            MarcusMode.CREATOR,
            reason="User requested creator mode",
            user_id="test_user"
        )
        
        assert result["success"] is True
        assert result["previous_mode"] == "adaptive"
        assert result["current_mode"] == "creator"
        assert result["reason"] == "User requested creator mode"
        assert mode_registry.current_mode == MarcusMode.CREATOR
        assert len(mode_registry.mode_history) == 1
        
        # Check mode switch history
        switch = mode_registry.mode_history[0]
        assert switch.from_mode == MarcusMode.ADAPTIVE
        assert switch.to_mode == MarcusMode.CREATOR
        assert switch.reason == "User requested creator mode"
        assert switch.user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_switch_mode_unimplemented(self, mode_registry):
        """Test switching to unimplemented mode fails gracefully"""
        result = await mode_registry.switch_mode(MarcusMode.ENRICHER)
        
        assert result["success"] is False
        assert "not yet implemented" in result["error"]
        assert result["current_mode"] == "adaptive"
        assert mode_registry.current_mode == MarcusMode.ADAPTIVE
        assert len(mode_registry.mode_history) == 0
    
    @pytest.mark.asyncio
    async def test_state_preservation_on_switch(self, mode_registry):
        """Test mode state is preserved when switching modes"""
        # Switch to creator mode
        await mode_registry.switch_mode(MarcusMode.CREATOR)
        
        # Verify state was saved from adaptive mode
        creator_handler = mode_registry.modes[MarcusMode.CREATOR]
        adaptive_handler = mode_registry.modes[MarcusMode.ADAPTIVE]
        
        # Check adaptive state was saved
        adaptive_handler.get_state.assert_called_once()
        assert mode_registry.mode_state[MarcusMode.ADAPTIVE] == {"adaptive_state": "running"}
        
        # Check creator was initialized with its saved state
        creator_handler.initialize.assert_called_once_with({})
    
    @pytest.mark.asyncio
    async def test_multiple_mode_switches(self, mode_registry):
        """Test multiple mode switches maintain proper history"""
        # Switch to creator
        await mode_registry.switch_mode(MarcusMode.CREATOR, reason="First switch")
        
        # Switch back to adaptive
        await mode_registry.switch_mode(MarcusMode.ADAPTIVE, reason="Second switch")
        
        # Switch to creator again
        await mode_registry.switch_mode(MarcusMode.CREATOR, reason="Third switch")
        
        assert len(mode_registry.mode_history) == 3
        assert mode_registry.current_mode == MarcusMode.CREATOR
        
        # Verify history order
        assert mode_registry.mode_history[0].to_mode == MarcusMode.CREATOR
        assert mode_registry.mode_history[1].to_mode == MarcusMode.ADAPTIVE
        assert mode_registry.mode_history[2].to_mode == MarcusMode.CREATOR
    
    @pytest.mark.asyncio
    async def test_get_current_mode_info(self, mode_registry):
        """Test getting current mode information"""
        info = await mode_registry.get_current_mode()
        
        assert info["current_mode"] == "adaptive"
        assert info["available"] is True
        assert info["switch_history"] == 0
        assert "capabilities" in info
        assert len(info["capabilities"]) > 0
        assert "description" in info
        assert "status" in info
        assert info["status"] == {"status": "operational"}
    
    @pytest.mark.asyncio
    async def test_get_current_mode_after_switch(self, mode_registry):
        """Test mode info updates after switching"""
        await mode_registry.switch_mode(MarcusMode.CREATOR)
        info = await mode_registry.get_current_mode()
        
        assert info["current_mode"] == "creator"
        assert info["switch_history"] == 1
        assert info["status"] == {"status": "ready"}
    
    def test_get_available_modes(self, mode_registry):
        """Test getting available modes"""
        available = mode_registry.get_available_modes()
        
        assert available == {
            "creator": True,
            "enricher": False,
            "adaptive": True
        }
    
    def test_get_mode_handler_current(self, mode_registry):
        """Test getting handler for current mode"""
        handler = mode_registry.get_mode_handler()
        assert handler is mode_registry.modes[MarcusMode.ADAPTIVE]
    
    def test_get_mode_handler_specific(self, mode_registry):
        """Test getting handler for specific mode"""
        handler = mode_registry.get_mode_handler(MarcusMode.CREATOR)
        assert handler is mode_registry.modes[MarcusMode.CREATOR]
    
    def test_get_mode_handler_unimplemented(self, mode_registry):
        """Test getting handler for unimplemented mode returns None"""
        handler = mode_registry.get_mode_handler(MarcusMode.ENRICHER)
        assert handler is None
    
    def test_get_mode_description(self, mode_registry):
        """Test mode descriptions are properly returned"""
        desc_creator = mode_registry._get_mode_description(MarcusMode.CREATOR)
        desc_adaptive = mode_registry._get_mode_description(MarcusMode.ADAPTIVE)
        desc_enricher = mode_registry._get_mode_description(MarcusMode.ENRICHER)
        
        assert "Create new project" in desc_creator
        assert "Coordinate work" in desc_adaptive
        assert "Organize and enrich" in desc_enricher
    
    def test_get_mode_history_empty(self, mode_registry):
        """Test mode history when no switches have occurred"""
        history = mode_registry.get_mode_history()
        assert history == []
    
    @pytest.mark.asyncio
    async def test_get_mode_history_with_switches(self, mode_registry):
        """Test mode history after multiple switches"""
        # Make several switches
        await mode_registry.switch_mode(MarcusMode.CREATOR, reason="Switch 1", user_id="user1")
        await mode_registry.switch_mode(MarcusMode.ADAPTIVE, reason="Switch 2", user_id="user2")
        
        history = mode_registry.get_mode_history()
        
        assert len(history) == 2
        # History is returned in reverse order (most recent first)
        assert history[0]["from"] == "creator"
        assert history[0]["to"] == "adaptive"
        assert history[0]["reason"] == "Switch 2"
        assert history[0]["user_id"] == "user2"
        
        assert history[1]["from"] == "adaptive"
        assert history[1]["to"] == "creator"
        assert history[1]["reason"] == "Switch 1"
        assert history[1]["user_id"] == "user1"
    
    @pytest.mark.asyncio
    async def test_get_mode_history_limited(self, mode_registry):
        """Test mode history respects limit parameter"""
        # Make many switches
        for i in range(15):
            mode = MarcusMode.CREATOR if i % 2 == 0 else MarcusMode.ADAPTIVE
            await mode_registry.switch_mode(mode, reason=f"Switch {i}")
        
        history = mode_registry.get_mode_history(limit=5)
        assert len(history) == 5
    
    @pytest.mark.asyncio
    async def test_suggest_mode_switch_empty_board(self, mode_registry):
        """Test mode suggestion for empty board"""
        board_state = Mock(spec=BoardState)
        board_state.is_empty = True
        board_state.is_chaotic = False
        board_state.is_well_structured = False
        
        suggestion = await mode_registry.suggest_mode_switch(board_state)
        
        assert suggestion is not None
        assert suggestion["suggest_switch"] is True
        assert suggestion["from_mode"] == "adaptive"
        assert suggestion["to_mode"] == "creator"
        assert "empty" in suggestion["reason"]
    
    @pytest.mark.asyncio
    async def test_suggest_mode_switch_chaotic_board(self, mode_registry):
        """Test mode suggestion for chaotic board when enricher is available"""
        # Mock enricher as available
        mode_registry.modes[MarcusMode.ENRICHER] = Mock()
        
        board_state = Mock(spec=BoardState)
        board_state.is_empty = False
        board_state.is_chaotic = True
        board_state.is_well_structured = False
        board_state.task_count = 42
        
        suggestion = await mode_registry.suggest_mode_switch(board_state)
        
        assert suggestion is not None
        assert suggestion["suggest_switch"] is True
        assert suggestion["to_mode"] == "enricher"
        assert "42 tasks" in suggestion["reason"]
        assert "organization" in suggestion["reason"]
    
    @pytest.mark.asyncio
    async def test_suggest_mode_switch_well_structured(self, mode_registry):
        """Test mode suggestion for well-structured board"""
        # Start in creator mode
        await mode_registry.switch_mode(MarcusMode.CREATOR)
        
        # Mock the timestamp to be > 5 minutes ago
        mode_registry.mode_history[-1].timestamp = datetime.now() - timedelta(minutes=6)
        
        board_state = Mock(spec=BoardState)
        board_state.is_empty = False
        board_state.is_chaotic = False
        board_state.is_well_structured = True
        
        suggestion = await mode_registry.suggest_mode_switch(board_state)
        
        assert suggestion is not None
        assert suggestion["suggest_switch"] is True
        assert suggestion["from_mode"] == "creator"
        assert suggestion["to_mode"] == "adaptive"
        assert "well-structured" in suggestion["reason"]
    
    @pytest.mark.asyncio
    async def test_suggest_mode_switch_no_suggestion(self, mode_registry):
        """Test when no mode switch is suggested"""
        # Already in creator mode with empty board
        await mode_registry.switch_mode(MarcusMode.CREATOR)
        
        board_state = Mock(spec=BoardState)
        board_state.is_empty = True
        board_state.is_chaotic = False
        board_state.is_well_structured = False
        
        suggestion = await mode_registry.suggest_mode_switch(board_state)
        
        assert suggestion is None
    
    @pytest.mark.asyncio
    async def test_suggest_mode_switch_recent_switch(self, mode_registry):
        """Test no suggestion if recently switched"""
        # Make a switch
        await mode_registry.switch_mode(MarcusMode.CREATOR)
        
        board_state = Mock(spec=BoardState)
        board_state.is_empty = False
        board_state.is_chaotic = False
        board_state.is_well_structured = True
        
        # Should not suggest because we just switched
        suggestion = await mode_registry.suggest_mode_switch(board_state)
        
        assert suggestion is None
    
    @pytest.mark.asyncio
    async def test_suggest_mode_switch_after_cooldown(self, mode_registry):
        """Test suggestion works after cooldown period"""
        # Make a switch
        await mode_registry.switch_mode(MarcusMode.CREATOR)
        
        # Mock the timestamp to be > 5 minutes ago
        mode_registry.mode_history[-1].timestamp = datetime.now() - timedelta(minutes=6)
        
        board_state = Mock(spec=BoardState)
        board_state.is_empty = False
        board_state.is_chaotic = False
        board_state.is_well_structured = True
        
        # Should suggest now that cooldown has passed
        suggestion = await mode_registry.suggest_mode_switch(board_state)
        
        assert suggestion is not None
        assert suggestion["to_mode"] == "adaptive"
    
    @pytest.mark.asyncio
    async def test_mode_without_get_state_method(self, mode_registry):
        """Test switching from mode without get_state method"""
        # Mock a mode without get_state
        mock_mode = Mock()
        del mock_mode.get_state  # Ensure it doesn't have this attribute
        mode_registry.modes[MarcusMode.ADAPTIVE] = mock_mode
        
        # Should not crash when switching away
        result = await mode_registry.switch_mode(MarcusMode.CREATOR)
        
        assert result["success"] is True
        assert mode_registry.mode_state[MarcusMode.ADAPTIVE] == {}
    
    @pytest.mark.asyncio
    async def test_mode_without_initialize_method(self, mode_registry):
        """Test switching to mode without initialize method"""
        # Mock a mode without initialize
        mock_mode = Mock()
        del mock_mode.initialize  # Ensure it doesn't have this attribute
        mode_registry.modes[MarcusMode.CREATOR] = mock_mode
        
        # Should not crash when switching to it
        result = await mode_registry.switch_mode(MarcusMode.CREATOR)
        
        assert result["success"] is True
        assert mode_registry.current_mode == MarcusMode.CREATOR
    
    @pytest.mark.asyncio
    async def test_mode_without_get_status_method(self, mode_registry):
        """Test getting info for mode without get_status method"""
        # Mock a mode without get_status
        mock_mode = Mock()
        del mock_mode.get_status  # Ensure it doesn't have this attribute
        mode_registry.modes[MarcusMode.ADAPTIVE] = mock_mode
        
        info = await mode_registry.get_current_mode()
        
        assert "status" not in info
        assert info["current_mode"] == "adaptive"
        assert info["available"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_mode_switches(self, mode_registry):
        """Test registry handles rapid mode switches correctly"""
        # Simulate concurrent switches
        results = []
        
        async def switch_task(mode, reason):
            result = await mode_registry.switch_mode(mode, reason=reason)
            results.append(result)
        
        # Execute switches in sequence (simulating near-concurrent execution)
        await switch_task(MarcusMode.CREATOR, "Switch 1")
        await switch_task(MarcusMode.ADAPTIVE, "Switch 2")
        await switch_task(MarcusMode.CREATOR, "Switch 3")
        
        # All switches should succeed
        assert all(r["success"] for r in results)
        assert len(mode_registry.mode_history) == 3
        assert mode_registry.current_mode == MarcusMode.CREATOR
    
    def test_mode_switch_dataclass(self):
        """Test ModeSwitch dataclass creation"""
        switch = ModeSwitch(
            from_mode=MarcusMode.ADAPTIVE,
            to_mode=MarcusMode.CREATOR,
            timestamp=datetime.now(),
            reason="Test switch",
            user_id="test_user"
        )
        
        assert switch.from_mode == MarcusMode.ADAPTIVE
        assert switch.to_mode == MarcusMode.CREATOR
        assert switch.reason == "Test switch"
        assert switch.user_id == "test_user"
        assert isinstance(switch.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_state_isolation_between_modes(self, mode_registry):
        """Test that mode states are properly isolated"""
        # Set up different states for each mode
        creator_state = {"projects": ["project1", "project2"]}
        adaptive_state = {"agents": ["agent1", "agent2"]}
        
        mode_registry.modes[MarcusMode.CREATOR].get_state = AsyncMock(return_value=creator_state)
        mode_registry.modes[MarcusMode.ADAPTIVE].get_state = AsyncMock(return_value=adaptive_state)
        
        # Switch between modes
        await mode_registry.switch_mode(MarcusMode.CREATOR)
        await mode_registry.switch_mode(MarcusMode.ADAPTIVE)
        
        # Verify states are kept separate
        assert mode_registry.mode_state[MarcusMode.CREATOR] == creator_state
        assert mode_registry.mode_state[MarcusMode.ADAPTIVE] == adaptive_state
    
    @pytest.mark.asyncio
    async def test_initialize_with_previous_state(self, mode_registry):
        """Test mode initialization with previously saved state"""
        # Set up saved state
        saved_state = {"restored": True, "data": [1, 2, 3]}
        mode_registry.mode_state[MarcusMode.CREATOR] = saved_state
        
        # Switch to creator mode
        await mode_registry.switch_mode(MarcusMode.CREATOR)
        
        # Verify it was initialized with saved state
        creator_handler = mode_registry.modes[MarcusMode.CREATOR]
        creator_handler.initialize.assert_called_once_with(saved_state)
    
    @pytest.mark.asyncio
    async def test_suggest_mode_switch_no_condition_met(self, mode_registry):
        """Test no suggestion when board state doesn't match any condition"""
        # Mock the timestamp to avoid recent switch restriction
        await mode_registry.switch_mode(MarcusMode.ADAPTIVE)
        mode_registry.mode_history[-1].timestamp = datetime.now() - timedelta(minutes=6)
        
        board_state = Mock(spec=BoardState)
        board_state.is_empty = False
        board_state.is_chaotic = False
        board_state.is_well_structured = False  # No specific condition
        
        suggestion = await mode_registry.suggest_mode_switch(board_state)
        
        assert suggestion is None