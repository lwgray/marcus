#!/usr/bin/env python3
"""Test MCP server setup"""

from mcp.server import Server

def test_server():
    server = Server("test-server")
    print(f"Server created: {server}")
    print(f"Server attributes: {dir(server)}")
    
    # Check for tool decorator
    if hasattr(server, 'tool'):
        print("✓ Server has 'tool' method")
    else:
        print("✗ Server does NOT have 'tool' method")
        
    # Try to access tools list
    if hasattr(server, 'list_tools'):
        print("✓ Server has 'list_tools' method")
        try:
            tools = server.list_tools()
            print(f"  Tools: {tools}")
        except Exception as e:
            print(f"  Error listing tools: {e}")

if __name__ == "__main__":
    test_server()