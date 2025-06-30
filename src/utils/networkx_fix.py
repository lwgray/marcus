"""
NetworkX race condition fix for Marcus

This module provides a fix for the "dictionary changed size during iteration" 
error that occurs in NetworkX 3.4.2 when used in async/concurrent environments.
"""

import threading


def apply_networkx_thread_safety_fix():
    """
    Apply thread safety fix to NetworkX to prevent race conditions.
    
    This fixes the "dictionary changed size during iteration" error
    that occurs in NetworkX's configuration management.
    """
    try:
        import networkx as nx
        from networkx.utils import configs
        
        # Create a lock for NetworkX config access
        if not hasattr(configs, '_marcus_lock'):
            configs._marcus_lock = threading.RLock()
        
        # Monkey patch the config iteration to be thread-safe
        if hasattr(configs, 'config') and hasattr(configs.config, '__iter__'):
            original_iter = configs.config.__iter__
            
            def thread_safe_iter(self):
                with configs._marcus_lock:
                    # Create a snapshot of the dictionary keys
                    return iter(list(original_iter(self)))
            
            configs.config.__iter__ = thread_safe_iter.__get__(configs.config)
            
        print("✅ NetworkX thread safety fix applied")
        return True
        
    except ImportError:
        print("ℹ️  NetworkX not available, skipping thread safety fix")
        return False
    except Exception as e:
        print(f"⚠️  Failed to apply NetworkX thread safety fix: {e}")
        return False


def ensure_networkx_safety():
    """
    Ensure NetworkX is used safely in Marcus.
    
    This should be called before any NetworkX operations in concurrent environments.
    """
    return apply_networkx_thread_safety_fix()