Getting Started
===============

Welcome to PM Agent! This guide will help you get up and running quickly.

Prerequisites
-------------

Before you begin, ensure you have:

* Python 3.8 or higher
* Node.js 18 or higher
* Docker (for Planka, included with kanban-mcp)
* Git
* Anthropic API key (optional, for AI features)

Quick Installation
------------------

1. **Clone the repositories**::

    # Clone kanban-mcp (includes Planka)
    git clone https://github.com/bradrisse/kanban-mcp.git
    cd kanban-mcp
    npm install
    npm run build
    
    # Clone PM Agent
    cd ..
    git clone https://github.com/lwgray/pm-agent.git
    cd pm-agent
    pip install -r requirements.txt

2. **Start Planka**::

    cd ../kanban-mcp
    npm run up

   Access Planka at http://localhost:3333 with credentials: demo@demo.demo / demo

3. **Configure PM Agent**::

    cd ../pm-agent
    cp .env.example .env
    # Add your ANTHROPIC_API_KEY to .env

4. **Verify setup**::

    python scripts/utilities/test_setup.py

Next Steps
----------

* :doc:`configuration` - Configure PM Agent for your project
* :doc:`usage` - Learn how to use PM Agent
* :doc:`mcp_tools` - Explore available MCP tools
* :doc:`worker_agents` - Build compatible worker agents