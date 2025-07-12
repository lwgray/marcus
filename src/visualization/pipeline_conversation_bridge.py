"""
Minimal stubs for pipeline conversation bridge
"""

from typing import Any, Dict, Optional


class PipelineConversationBridge:
    """Minimal stub for bridging pipeline events and conversations"""

    def __init__(self):
        self.conversation_log = []

    def log_pipeline_conversation(
        self,
        pipeline_id: str,
        stage: str,
        message: str,
        metadata: Dict[str, Any] = None,
    ):
        """Log a conversation event tied to pipeline"""
        entry = {
            "pipeline_id": pipeline_id,
            "stage": stage,
            "message": message,
            "metadata": metadata or {},
            "timestamp": None,  # Will be set by conversation logger
        }
        self.conversation_log.append(entry)

    def get_pipeline_conversations(self, pipeline_id: str) -> list:
        """Get conversations for a specific pipeline"""
        return [
            entry
            for entry in self.conversation_log
            if entry["pipeline_id"] == pipeline_id
        ]

    def bridge_to_conversation_logger(self, conversation_logger):
        """Bridge pipeline events to conversation logger"""
        # This would normally integrate with the conversation logger
        # For now, it's just a stub
        pass
