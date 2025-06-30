"""Data flow visualization system for Marcus"""

from .conversation_stream import ConversationStreamProcessor
# Lazy imports to avoid loading NetworkX unless needed
# from .decision_visualizer import DecisionVisualizer
# from .knowledge_graph import KnowledgeGraphBuilder
from .ui_server import VisualizationServer

def get_decision_visualizer():
    """Lazy import DecisionVisualizer to avoid NetworkX import"""
    from .decision_visualizer import DecisionVisualizer
    return DecisionVisualizer

def get_knowledge_graph_builder():
    """Lazy import KnowledgeGraphBuilder to avoid NetworkX import"""
    from .knowledge_graph import KnowledgeGraphBuilder
    return KnowledgeGraphBuilder

__all__ = [
    'ConversationStreamProcessor',
    'get_decision_visualizer', 
    'get_knowledge_graph_builder',
    'VisualizationServer'
]