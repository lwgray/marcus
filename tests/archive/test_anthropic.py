#!/usr/bin/env python3
"""
Test Anthropic client initialization
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def test_anthropic():
    """Test Anthropic client initialization"""
    print("🧪 Testing Anthropic Client")
    print("=" * 50)
    
    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment")
        print("\nPlease set it:")
        print("export ANTHROPIC_API_KEY=your-api-key")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    # Test import
    try:
        import anthropic
        print(f"✅ Anthropic module imported: version {anthropic.__version__ if hasattr(anthropic, '__version__') else 'unknown'}")
    except ImportError as e:
        print(f"❌ Failed to import anthropic: {e}")
        print("\nTry: pip install anthropic")
        return False
    
    # Test client initialization
    try:
        # Simple initialization without any extra parameters
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ Client initialized successfully")
        
        # Test a simple API call
        print("\n📝 Testing API call...")
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            messages=[
                {"role": "user", "content": "Say 'PM Agent test successful' and nothing else"}
            ]
        )
        print(f"✅ API Response: {response.content[0].text}")
        
    except Exception as e:
        print(f"❌ Client initialization or API call failed: {e}")
        print(f"\nError type: {type(e).__name__}")
        
        # Check if it's the proxies error
        if "proxies" in str(e):
            print("\n⚠️  Proxies parameter issue detected")
            print("This might be due to an incompatible anthropic version")
            print("\nTry updating anthropic:")
            print("pip install --upgrade anthropic")
        
        return False
    
    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_anthropic()
    sys.exit(0 if success else 1)