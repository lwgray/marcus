#!/usr/bin/env python3
"""
Debug the Anthropic proxies error
"""

import os
import sys
import inspect

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def debug_anthropic():
    """Debug Anthropic initialization"""
    print("🔍 Debugging Anthropic Initialization")
    print("=" * 50)
    
    # Check anthropic module
    try:
        import anthropic
        print(f"✅ Anthropic imported from: {anthropic.__file__}")
        print(f"   Version: {getattr(anthropic, '__version__', 'unknown')}")
    except ImportError as e:
        print(f"❌ Cannot import anthropic: {e}")
        return
    
    # Check the Anthropic class signature
    print("\n📝 Checking Anthropic class...")
    try:
        sig = inspect.signature(anthropic.Anthropic.__init__)
        print(f"   Parameters: {list(sig.parameters.keys())}")
    except Exception as e:
        print(f"   Error inspecting signature: {e}")
    
    # Try different initialization methods
    print("\n🧪 Testing initialization methods...")
    
    # Method 1: Just API key
    print("\n1. Simple initialization (api_key only):")
    try:
        client = anthropic.Anthropic(api_key="test-key")
        print("   ✅ Success!")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        print(f"   Error type: {type(e).__name__}")
    
    # Method 2: With explicit kwargs
    print("\n2. Explicit keyword argument:")
    try:
        client = anthropic.Anthropic(api_key="test-key")
        print("   ✅ Success!")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Check if something is modifying the class
    print("\n🔍 Checking for monkey patches...")
    original_init = anthropic.Anthropic.__init__
    print(f"   __init__ method: {original_init}")
    print(f"   Module: {original_init.__module__ if hasattr(original_init, '__module__') else 'unknown'}")
    
    # Check environment
    print("\n🌍 Checking environment...")
    proxy_vars = [k for k in os.environ.keys() if 'proxy' in k.lower()]
    if proxy_vars:
        print(f"   Found proxy variables: {proxy_vars}")
        for var in proxy_vars:
            print(f"   {var} = {os.environ[var]}")
    else:
        print("   No proxy environment variables found")
    
    # Check if we have any startup scripts modifying behavior
    print("\n📁 Checking for startup modifications...")
    for path in sys.path[:5]:  # Check first few paths
        print(f"   {path}")
    
    # Try importing our AI engine to see if it's the issue
    print("\n🤖 Testing AI Analysis Engine import...")
    try:
        from src.integrations.ai_analysis_engine import AIAnalysisEngine
        print("   ✅ AIAnalysisEngine imported")
        
        # Try initializing it
        engine = AIAnalysisEngine()
        print("   ✅ AIAnalysisEngine initialized")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_anthropic()