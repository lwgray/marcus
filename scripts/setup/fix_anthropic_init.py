#!/usr/bin/env python3
"""
Fix Anthropic initialization issues
"""

import subprocess
import sys
import os


def fix_anthropic():
    """Fix Anthropic client issues"""
    print("🔧 Fixing Anthropic Client Issues")
    print("=" * 50)
    
    # Check current version
    print("\n1️⃣ Checking current anthropic version...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "anthropic"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    print(f"   Current version: {line.split(':')[1].strip()}")
        else:
            print("   Anthropic not installed")
    except Exception as e:
        print(f"   Error checking version: {e}")
    
    # Uninstall old version
    print("\n2️⃣ Uninstalling old anthropic...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "anthropic"])
    
    # Install compatible version
    print("\n3️⃣ Installing compatible anthropic version...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "anthropic==0.18.1"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("   ✅ Installed anthropic 0.18.1")
    else:
        print(f"   ❌ Installation failed: {result.stderr}")
        return False
    
    # Test import
    print("\n4️⃣ Testing import...")
    try:
        import anthropic
        print(f"   ✅ Import successful")
        
        # Test initialization
        api_key = os.environ.get("ANTHROPIC_API_KEY", "test-key")
        client = anthropic.Anthropic(api_key=api_key)
        print("   ✅ Client initialization successful")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n✅ Anthropic client fixed!")
    print("\nNext steps:")
    print("1. Make sure ANTHROPIC_API_KEY is set in your environment")
    print("2. Run: python start_pm_agent_task_master.py")
    
    return True


if __name__ == "__main__":
    success = fix_anthropic()
    sys.exit(0 if success else 1)