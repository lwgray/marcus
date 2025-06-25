#!/usr/bin/env python3
"""
Test Connection Script for PM Agent
Verifies all connections are working properly
"""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.kanban_factory import KanbanFactory
from src.config.settings import Settings


async def test_kanban_connection():
    """Test connection to the configured Kanban provider."""
    print("🔌 Testing Kanban Connection")
    print("-" * 40)
    
    try:
        settings = Settings()
        print(f"Provider: {settings.KANBAN_PROVIDER}")
        
        # Create kanban client
        kanban = KanbanFactory.create(
            provider=settings.KANBAN_PROVIDER,
            config=settings.get_provider_config()
        )
        
        # Test basic connection by getting boards
        print("Fetching boards...")
        boards = await kanban.get_boards()
        
        if boards:
            print(f"✅ Connected successfully! Found {len(boards)} board(s):")
            for i, board in enumerate(boards[:5], 1):  # Show max 5 boards
                print(f"   {i}. {board.get('name', 'Unnamed')}")
            if len(boards) > 5:
                print(f"   ... and {len(boards) - 5} more")
        else:
            print("⚠️  Connected but no boards found")
            print("   Create a board first or check your configuration")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        
        # Provider-specific troubleshooting
        if settings.KANBAN_PROVIDER == "github":
            print("\n💡 GitHub troubleshooting:")
            print("   1. Check GITHUB_TOKEN has 'repo' and 'project' scopes")
            print("   2. Verify GITHUB_OWNER and GITHUB_REPO are correct")
            print("   3. Ensure the repository exists and you have access")
        elif settings.KANBAN_PROVIDER == "linear":
            print("\n💡 Linear troubleshooting:")
            print("   1. Check LINEAR_API_KEY is valid")
            print("   2. Verify LINEAR_TEAM_ID is correct")
            print("   3. Ensure you have access to the team")
        elif settings.KANBAN_PROVIDER == "planka":
            print("\n💡 Planka troubleshooting:")
            print("   1. Ensure Planka is running (docker-compose ps)")
            print("   2. Check PLANKA_PROJECT_NAME exists")
            print("   3. Verify Planka is accessible at http://localhost:1337")
        
        return False


def test_api_keys():
    """Test that required API keys are configured."""
    print("\n🔑 Testing API Keys")
    print("-" * 40)
    
    all_good = True
    
    # Check Anthropic API key
    if os.environ.get("ANTHROPIC_API_KEY"):
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key.startswith("sk-ant-"):
            print("✅ ANTHROPIC_API_KEY is set and formatted correctly")
        else:
            print("⚠️  ANTHROPIC_API_KEY is set but may be incorrectly formatted")
            print("   Should start with 'sk-ant-'")
    else:
        print("❌ ANTHROPIC_API_KEY is not set")
        print("   AI workers will not function without this key")
        all_good = False
    
    # Check optional OpenAI key
    if os.environ.get("OPENAI_API_KEY"):
        print("✅ OPENAI_API_KEY is set (optional)")
    else:
        print("ℹ️  OPENAI_API_KEY is not set (optional)")
    
    return all_good


def test_docker_status():
    """Test if running in Docker and check container status."""
    print("\n🐳 Testing Docker Status")
    print("-" * 40)
    
    # Check if we're running in Docker
    if os.path.exists("/.dockerenv"):
        print("✅ Running inside Docker container")
    else:
        print("ℹ️  Not running in Docker (native Python execution)")
        
        # Try to check Docker status from outside
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("\nDocker containers:")
                print(result.stdout)
            else:
                print("⚠️  Could not check Docker status")
        except:
            print("ℹ️  Docker command not available")
    
    return True


def test_file_permissions():
    """Test that we can write to necessary directories."""
    print("\n📁 Testing File Permissions")
    print("-" * 40)
    
    dirs_to_test = [
        ("logs", "Log files"),
        ("data", "Data storage"),
        ("output", "Generated code")
    ]
    
    all_good = True
    
    for dir_name, description in dirs_to_test:
        try:
            # Create directory if it doesn't exist
            os.makedirs(dir_name, exist_ok=True)
            
            # Try to write a test file
            test_file = os.path.join(dir_name, ".test_write")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            
            print(f"✅ Can write to {dir_name}/ ({description})")
        except Exception as e:
            print(f"❌ Cannot write to {dir_name}/ ({description}): {e}")
            all_good = False
    
    return all_good


async def main():
    """Run all connection tests."""
    print("🏥 PM Agent Connection Test")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run tests
    results = {
        "API Keys": test_api_keys(),
        "Docker": test_docker_status(),
        "File Permissions": test_file_permissions(),
        "Kanban Connection": await test_kanban_connection()
    }
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! PM Agent is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("\nFor more help:")
        print("  - Check the installation guide: docs/installation.md")
        print("  - See troubleshooting: docs/troubleshooting.md")
        print("  - Run with debug: PM_AGENT_DEBUG=true ./start.sh")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)