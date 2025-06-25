"""
Base class for all PM Agent experiments
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Callable

class BaseExperiment(ABC):
    """Abstract base class for experiments"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.results_dir = Path("./results") / self.__class__.__name__.lower()
        self.cache_dir = Path("./cache")
        self.data_dir = Path("./data")
        
        # Ensure directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    @abstractmethod
    async def run(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Run the experiment and return results
        
        Args:
            progress_callback: Optional callback for progress updates (percent, status)
            
        Returns:
            Dictionary containing experiment results
        """
        pass
    
    def validate_config(self):
        """Validate experiment configuration"""
        required_fields = self.get_required_config_fields()
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
    
    def get_required_config_fields(self) -> list:
        """Override to specify required configuration fields"""
        return []
    
    def save_checkpoint(self, data: Dict[str, Any], checkpoint_name: str):
        """Save intermediate results checkpoint"""
        import json
        checkpoint_path = self.results_dir / f"checkpoint_{checkpoint_name}.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Saved checkpoint: {checkpoint_path}")
    
    def load_checkpoint(self, checkpoint_name: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint if exists"""
        import json
        checkpoint_path = self.results_dir / f"checkpoint_{checkpoint_name}.json"
        if checkpoint_path.exists():
            with open(checkpoint_path, 'r') as f:
                return json.load(f)
        return None