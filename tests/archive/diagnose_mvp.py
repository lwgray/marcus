#!/usr/bin/env python3
"""
Quick diagnostic script to identify issues with PM Agent MVP
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

def check_imports():
    """Check if all required imports work"""
    print("🔍 Checking imports...")
    
    try:
        from mcp.server import Server
        print("✅ MCP server import: OK")
    except ImportError as e:
        print(f"❌ MCP server import failed: {e}")
        return False
    
    try:
        from mcp.types import Tool, TextContent
        print("✅ MCP types import: OK")
    except ImportError as e:
        print(f"❌ MCP types import failed: {e}")
        return False
    
    try:
        import anthropic
        print("✅ Anthropic import: OK")
    except ImportError as e:
        print(f"❌ Anthropic import failed: {e}")
        return False
    
    try:
        from src.core.models import Task, TaskStatus, Priority, WorkerStatus, TaskAssignment
        print("✅ Core models import: OK")
    except ImportError as e:
        print(f"❌ Core models import failed: {e}")
        return False
    
    try:
        from src.integrations.mcp_kanban_client import MCPKanbanClient
        print("✅ Kanban client import: OK")
    except ImportError as e:
        print(f"❌ Kanban client import failed: {e}")
        return False
    
    try:
        from src.integrations.ai_analysis_engine import AIAnalysisEngine
        print("✅ AI engine import: OK")
    except ImportError as e:
        print(f"❌ AI engine import failed: {e}")
        return False
    
    try:
        from src.config.settings import Settings
        print("✅ Settings import: OK")
    except ImportError as e:
        print(f"❌ Settings import failed: {e}")
        return False
    
    return True

def check_environment():
    """Check environment variables and configuration"""
    print("\n🌍 Checking environment...")
    
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        print("✅ ANTHROPIC_API_KEY: Set")
    else:
        print("⚠️  ANTHROPIC_API_KEY: Not set (AI features may not work)")
    
    # Check config file
    config_path = "config/pm_agent_config.json"
    if os.path.exists(config_path):
        print("✅ Config file: Found")
    else:
        print("⚠️  Config file: Missing (using defaults)")
    
    return True

def check_dependencies():
    """Check if dependencies are installed"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        "mcp",
        "anthropic", 
        "asyncio",
        "python-dotenv"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}: Installed")
        except ImportError:
            print(f"❌ {package}: Missing")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    return True

def test_basic_initialization():
    """Test basic class initialization"""
    print("\n🧪 Testing basic initialization...")
    
    try:
        # Test imports work
        from pm_agent_mvp_fixed import PMAgentMVP
        print("✅ MVP class import: OK")
        
        # Test initialization
        agent = PMAgentMVP()
        print("✅ MVP initialization: OK")
        
        # Test that components are created
        if hasattr(agent, 'kanban_client'):
            print("✅ Kanban client created: OK")
        else:
            print("❌ Kanban client: Missing")
            return False
        
        if hasattr(agent, 'ai_engine'):
            print("✅ AI engine created: OK")
        else:
            print("❌ AI engine: Missing")
            return False
        
        if hasattr(agent, 'server'):
            print("✅ MCP server created: OK")
        else:
            print("❌ MCP server: Missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic checks"""
    print("🏥 PM Agent MVP Diagnostic")
    print("=" * 40)
    
    checks = [
        ("Import Check", check_imports),
        ("Environment Check", check_environment), 
        ("Dependencies Check", check_dependencies),
        ("Initialization Check", test_basic_initialization)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} crashed: {e}")
            results.append((name, False))
    
    print("\n📋 Summary:")
    print("=" * 40)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! Try running:")
        print("python pm_agent_mvp_fixed.py")
    else:
        print("\n🚨 Some checks failed. Fix the issues above before running the MVP.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
