#!/usr/bin/env python3
"""
Fix script to ensure Anthropic client initializes correctly
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def patch_anthropic_init():
    """Patch Anthropic initialization to handle proxy issues"""
    import anthropic
    
    # Store original init
    original_init = anthropic.Anthropic.__init__
    
    def patched_init(self, *args, **kwargs):
        """Patched init that filters out problematic proxy settings"""
        # Remove proxies if it's causing issues
        if 'proxies' in kwargs and kwargs['proxies'] is not None:
            # Check if proxies is a dict or something else
            if not isinstance(kwargs['proxies'], dict):
                print(f"Warning: Invalid proxies type: {type(kwargs['proxies'])}, removing", file=sys.stderr)
                kwargs.pop('proxies')
        
        # Call original init
        return original_init(self, *args, **kwargs)
    
    # Apply patch
    anthropic.Anthropic.__init__ = patched_init
    print("✅ Applied Anthropic initialization patch", file=sys.stderr)

if __name__ == "__main__":
    # Apply the patch
    patch_anthropic_init()
    
    # Now test
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test initialization
    print("Testing patched initialization...")
    from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
    engine = AIAnalysisEngine()
    print("✅ AIAnalysisEngine initialized successfully with patch")