#!/usr/bin/env python3
"""Test Kanban MCP authentication"""

import asyncio
import aiohttp
import os

async def test_planka_auth():
    """Test if we can authenticate with Planka directly"""
    print("🔍 Testing Planka Authentication")
    print("-" * 50)
    
    base_url = "http://localhost:3333"
    email = "demo@demo.demo"
    password = "demo"
    
    print(f"Base URL: {base_url}")
    print(f"Email: {email}")
    print(f"Password: {password}")
    
    # Test 1: Can we reach Planka?
    print("\n1. Testing Planka connectivity...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    print("   ✅ Planka is reachable")
                else:
                    print(f"   ❌ Unexpected status: {resp.status}")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return
    
    # Test 2: Try to authenticate
    print("\n2. Testing authentication...")
    try:
        async with aiohttp.ClientSession() as session:
            auth_url = f"{base_url}/api/access-tokens"
            auth_data = {
                "emailOrUsername": email,
                "password": password
            }
            
            async with session.post(auth_url, json=auth_data) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print("   ✅ Authentication successful!")
                    print(f"   Token: {data.get('item', {}).get('token', 'No token')[:20]}...")
                else:
                    text = await resp.text()
                    print(f"   ❌ Authentication failed: {resp.status}")
                    print(f"   Response: {text}")
    except Exception as e:
        print(f"   ❌ Auth request failed: {e}")
    
    # Test 3: Check environment
    print("\n3. Checking environment variables...")
    env_vars = ["PLANKA_BASE_URL", "PLANKA_AGENT_EMAIL", "PLANKA_AGENT_PASSWORD"]
    for var in env_vars:
        value = os.environ.get(var, "NOT SET")
        print(f"   {var}: {value}")

if __name__ == "__main__":
    asyncio.run(test_planka_auth())