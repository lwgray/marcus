"""
Configuration for Hybrid Dependency Inference

Allows tuning of thresholds to optimize the balance between
accuracy and API call costs.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class HybridInferenceConfig:
    """Configuration for hybrid dependency inference thresholds"""
    
    # Pattern matching thresholds
    pattern_confidence_threshold: float = 0.8
    """Pattern matches above this confidence don't need AI validation (0.0-1.0)
    Higher = more AI calls but better accuracy
    Lower = fewer AI calls but may miss complex dependencies
    Default: 0.8 (80% confidence)"""
    
    # AI analysis thresholds
    ai_confidence_threshold: float = 0.7
    """Minimum AI confidence to accept a dependency (0.0-1.0)
    Higher = more conservative, fewer false positives
    Lower = more permissive, may include weak dependencies
    Default: 0.7 (70% confidence)"""
    
    # Combination settings
    combined_confidence_boost: float = 0.15
    """Confidence boost when pattern and AI agree (0.0-0.3)
    Higher = stronger preference for agreement
    Lower = less weight on agreement
    Default: 0.15 (15% boost)"""
    
    # Performance settings
    max_ai_pairs_per_batch: int = 20
    """Maximum task pairs to analyze in one AI request
    Higher = fewer API calls but longer prompts
    Lower = more API calls but simpler prompts
    Default: 20 pairs"""
    
    min_shared_keywords: int = 2
    """Minimum shared keywords to consider tasks related
    Higher = fewer AI analyses, may miss subtle relationships
    Lower = more AI analyses, better coverage
    Default: 2 keywords"""
    
    # Cost control settings
    enable_ai_inference: bool = True
    """Master switch for AI inference
    True = Use hybrid approach
    False = Pattern-only (no API calls)
    Default: True"""
    
    cache_ttl_hours: int = 24
    """How long to cache AI inference results
    Higher = fewer repeat API calls
    Lower = more up-to-date analysis
    Default: 24 hours"""
    
    # Advanced settings
    require_component_match: bool = True
    """Whether tasks must share a component for pattern inference
    True = More accurate but may miss cross-component dependencies
    False = More permissive pattern matching
    Default: True"""
    
    max_dependency_chain_length: int = 10
    """Maximum length of dependency chains to prevent cycles
    Higher = Allow deeper task hierarchies
    Lower = Simpler, flatter task structures
    Default: 10"""
    
    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> 'HybridInferenceConfig':
        """Create config from dictionary"""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'pattern_confidence_threshold': self.pattern_confidence_threshold,
            'ai_confidence_threshold': self.ai_confidence_threshold,
            'combined_confidence_boost': self.combined_confidence_boost,
            'max_ai_pairs_per_batch': self.max_ai_pairs_per_batch,
            'min_shared_keywords': self.min_shared_keywords,
            'enable_ai_inference': self.enable_ai_inference,
            'cache_ttl_hours': self.cache_ttl_hours,
            'require_component_match': self.require_component_match,
            'max_dependency_chain_length': self.max_dependency_chain_length
        }
    
    def validate(self) -> None:
        """Validate configuration values"""
        if not 0.0 <= self.pattern_confidence_threshold <= 1.0:
            raise ValueError("pattern_confidence_threshold must be between 0.0 and 1.0")
            
        if not 0.0 <= self.ai_confidence_threshold <= 1.0:
            raise ValueError("ai_confidence_threshold must be between 0.0 and 1.0")
            
        if not 0.0 <= self.combined_confidence_boost <= 0.3:
            raise ValueError("combined_confidence_boost must be between 0.0 and 0.3")
            
        if self.max_ai_pairs_per_batch < 1:
            raise ValueError("max_ai_pairs_per_batch must be at least 1")
            
        if self.min_shared_keywords < 1:
            raise ValueError("min_shared_keywords must be at least 1")
            
        if self.cache_ttl_hours < 0:
            raise ValueError("cache_ttl_hours must be non-negative")


# Preset configurations for different use cases
PRESETS = {
    'conservative': HybridInferenceConfig(
        pattern_confidence_threshold=0.9,  # Only use AI for low confidence patterns
        ai_confidence_threshold=0.8,       # Require high AI confidence
        combined_confidence_boost=0.2,     # Strong preference for agreement
        max_ai_pairs_per_batch=10,         # Smaller batches for accuracy
        min_shared_keywords=3              # Stricter relatedness check
    ),
    
    'balanced': HybridInferenceConfig(
        # Use defaults
    ),
    
    'aggressive': HybridInferenceConfig(
        pattern_confidence_threshold=0.7,  # More AI validation
        ai_confidence_threshold=0.6,       # Accept more dependencies
        combined_confidence_boost=0.1,     # Less weight on agreement
        max_ai_pairs_per_batch=30,         # Larger batches for efficiency
        min_shared_keywords=1              # Looser relatedness check
    ),
    
    'cost_optimized': HybridInferenceConfig(
        pattern_confidence_threshold=0.85, # Trust patterns more
        ai_confidence_threshold=0.75,      # Moderate AI threshold
        max_ai_pairs_per_batch=50,         # Large batches to minimize calls
        cache_ttl_hours=48,                # Longer cache
        enable_ai_inference=True           # Still use AI but sparingly
    ),
    
    'pattern_only': HybridInferenceConfig(
        enable_ai_inference=False          # No API calls at all
    )
}


def get_preset_config(preset_name: str) -> HybridInferenceConfig:
    """Get a preset configuration by name"""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    return PRESETS[preset_name]