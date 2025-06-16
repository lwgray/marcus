#!/usr/bin/env python3
"""
Properly fix Anthropic version issues
"""

import subprocess
import sys
import os


def fix_anthropic_version():
    """Fix Anthropic version conflicts"""
    print("🔧 Fixing Anthropic Version Conflicts")
    print("=" * 50)
    
    # First, check what's installed
    print("\n1️⃣ Checking installed versions...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "|", "grep", "anthropic"],
        shell=True,
        capture_output=True,
        text=True
    )
    print(f"   Current installations:\n{result.stdout}")
    
    # Uninstall ALL versions
    print("\n2️⃣ Uninstalling all anthropic versions...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "anthropic"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Clear pip cache
    print("\n3️⃣ Clearing pip cache...")
    subprocess.run([sys.executable, "-m", "pip", "cache", "purge"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Install the correct version
    print("\n4️⃣ Installing anthropic 0.39.0 (which supports proxies parameter)...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "anthropic==0.39.0"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"   ❌ Installation failed: {result.stderr}")
        return False
    
    print("   ✅ Installed anthropic 0.39.0")
    
    # Now we need to find where proxies is being passed
    print("\n5️⃣ Checking AI Analysis Engine...")
    
    # The issue is that our AIAnalysisEngine is trying to use proxies
    # Let's check if there's a config setting it
    return True


def check_ai_engine_init():
    """Check how AI engine is being initialized"""
    print("\n🔍 Checking AI Engine initialization...")
    
    ai_engine_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 
        'src', 'integrations', 'ai_analysis_engine.py'
    )
    
    with open(ai_engine_path, 'r') as f:
        content = f.read()
        
    # Look for where Anthropic is initialized
    if 'proxies' in content:
        print("   ⚠️  Found 'proxies' in ai_analysis_engine.py")
    else:
        print("   ✅ No 'proxies' found in ai_analysis_engine.py")
        
    # The issue might be in a config file or environment
    return True


def test_final():
    """Test the final setup"""
    print("\n6️⃣ Testing final setup...")
    
    try:
        import anthropic
        print(f"   ✅ Anthropic version: {getattr(anthropic, '__version__', 'unknown')}")
        
        # Test with API key
        api_key = os.environ.get("ANTHROPIC_API_KEY", "sk-test-key")
        
        # Since 0.39.0 accepts proxies, let's use it
        client = anthropic.Anthropic(
            api_key=api_key,
            proxies=None  # Explicitly set to None
        )
        print("   ✅ Client initialized with proxies=None")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
        
    print("\n✅ Setup complete!")
    print("\nThe issue was version mismatch. anthropic 0.39.0 supports the proxies parameter.")
    print("The error suggests something is passing proxies when initializing.")
    print("\nNext: Let's check where proxies is being set...")
    
    return True


if __name__ == "__main__":
    if fix_anthropic_version():
        check_ai_engine_init()
        test_final()