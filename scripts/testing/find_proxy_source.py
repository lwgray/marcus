#!/usr/bin/env python3
"""
Find where the proxies parameter is coming from
"""

import os
import sys
import ast
import importlib.util

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def check_import_hooks():
    """Check if there are any import hooks modifying behavior"""
    print("🔍 Checking import hooks and sys.modules...")
    
    # Check for anthropic in sys.modules
    if 'anthropic' in sys.modules:
        print("   ⚠️  anthropic already in sys.modules before import")
        del sys.modules['anthropic']
    
    # Check meta path
    print("\n📦 Import meta path:")
    for finder in sys.meta_path[:3]:
        print(f"   {finder}")


def trace_anthropic_init():
    """Trace where Anthropic is being initialized with proxies"""
    print("\n🔍 Tracing Anthropic initialization...")
    
    # Monkey patch to trace calls
    import anthropic
    
    original_init = anthropic.Anthropic.__init__
    
    def traced_init(self, *args, **kwargs):
        print(f"\n🚨 Anthropic.__init__ called!")
        print(f"   Args: {args}")
        print(f"   Kwargs: {kwargs}")
        print(f"   Called from:")
        
        import traceback
        for line in traceback.format_stack()[-10:-1]:
            if 'site-packages' not in line and 'traced_init' not in line:
                print(f"   {line.strip()}")
        
        # Call original
        return original_init(self, *args, **kwargs)
    
    anthropic.Anthropic.__init__ = traced_init
    
    # Now try importing our AI engine
    print("\n🤖 Importing AI Analysis Engine with trace...")
    try:
        from src.integrations.ai_analysis_engine import AIAnalysisEngine
        engine = AIAnalysisEngine()
    except Exception as e:
        print(f"\n❌ Error during import: {e}")


def check_sitecustomize():
    """Check for sitecustomize or usercustomize scripts"""
    print("\n📁 Checking for site customization scripts...")
    
    # Check for sitecustomize
    try:
        import sitecustomize
        print(f"   ⚠️  Found sitecustomize: {sitecustomize.__file__}")
    except ImportError:
        print("   ✅ No sitecustomize.py found")
    
    # Check for usercustomize
    try:
        import usercustomize
        print(f"   ⚠️  Found usercustomize: {usercustomize.__file__}")
    except ImportError:
        print("   ✅ No usercustomize.py found")
    
    # Check PYTHONSTARTUP
    startup = os.environ.get('PYTHONSTARTUP')
    if startup:
        print(f"   ⚠️  PYTHONSTARTUP set to: {startup}")
    else:
        print("   ✅ No PYTHONSTARTUP set")


def check_conda_env():
    """Check conda environment for modifications"""
    print("\n🐍 Checking conda environment...")
    
    conda_prefix = os.environ.get('CONDA_PREFIX')
    if conda_prefix:
        print(f"   Conda environment: {conda_prefix}")
        
        # Check for activate scripts
        activate_dir = os.path.join(conda_prefix, 'etc', 'conda', 'activate.d')
        if os.path.exists(activate_dir):
            print(f"   Checking {activate_dir}...")
            for file in os.listdir(activate_dir):
                print(f"      - {file}")


if __name__ == "__main__":
    check_import_hooks()
    check_sitecustomize()
    check_conda_env()
    
    print("\n" + "=" * 50)
    trace_anthropic_init()