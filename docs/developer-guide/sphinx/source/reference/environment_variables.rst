Environment Variables
=====================

Complete reference of environment variables used by PM Agent.

Configuration File
------------------

PM Agent reads environment variables from a ``.env`` file in the project root:

.. code-block:: bash

   # Create from example
   cp .env.example .env
   
   # Edit with your values
   nano .env

Core Variables
--------------

Kanban Provider
~~~~~~~~~~~~~~~

.. envvar:: KANBAN_PROVIDER

   Specifies which task management system to use.
   
   :Valid values: ``github``, ``linear``, ``planka``
   :Default: ``planka``
   :Required: Yes
   
   Example::
   
      KANBAN_PROVIDER=github

AI Configuration
~~~~~~~~~~~~~~~~

.. envvar:: ANTHROPIC_API_KEY

   API key for Anthropic's Claude AI service.
   
   :Format: ``sk-ant-...``
   :Required: Yes (for AI features)
   :Fallback: Works without but limited to rule-based assignment
   
   Example::
   
      ANTHROPIC_API_KEY=sk-ant-api03-abc123...

.. envvar:: OPENAI_API_KEY

   API key for OpenAI (future use).
   
   :Format: ``sk-...``
   :Required: No
   :Status: Reserved for future features

GitHub Configuration
--------------------

Required when ``KANBAN_PROVIDER=github``:

.. envvar:: GITHUB_TOKEN

   Personal access token for GitHub API.
   
   :Permissions: ``repo``, ``project``
   :Format: ``ghp_...`` or ``github_pat_...``
   :Required: Yes (for GitHub provider)
   
   Example::
   
      GITHUB_TOKEN=ghp_1234567890abcdef

.. envvar:: GITHUB_OWNER

   GitHub username or organization name.
   
   :Format: Username without @ symbol
   :Required: Yes (for GitHub provider)
   
   Example::
   
      GITHUB_OWNER=octocat

.. envvar:: GITHUB_REPO

   Repository name for task management.
   
   :Format: Repository name only (not full URL)
   :Required: Yes (for GitHub provider)
   
   Example::
   
      GITHUB_REPO=my-project

Linear Configuration
--------------------

Required when ``KANBAN_PROVIDER=linear``:

.. envvar:: LINEAR_API_KEY

   API key for Linear.
   
   :Format: ``lin_api_...``
   :Required: Yes (for Linear provider)
   :Location: https://linear.app/settings/api
   
   Example::
   
      LINEAR_API_KEY=lin_api_abc123...

.. envvar:: LINEAR_TEAM_ID

   Your Linear team identifier.
   
   :Format: Team ID from Linear URL
   :Required: Yes (for Linear provider)
   
   Example::
   
      LINEAR_TEAM_ID=TEAM-123

Planka Configuration
--------------------

Used when ``KANBAN_PROVIDER=planka`` (local only):

.. envvar:: PLANKA_BASE_URL

   URL where Planka is running.
   
   :Default: ``http://localhost:3333``
   :Format: Full URL including protocol and port
   
   Example::
   
      PLANKA_BASE_URL=http://localhost:3333

.. envvar:: PLANKA_AGENT_EMAIL

   Email for Planka authentication.
   
   :Default: ``demo@demo.demo``
   :Note: Use default for local development
   
   Example::
   
      PLANKA_AGENT_EMAIL=pm-agent@example.com

.. envvar:: PLANKA_AGENT_PASSWORD

   Password for Planka authentication.
   
   :Default: ``demo``
   :Security: Change in production!
   
   Example::
   
      PLANKA_AGENT_PASSWORD=secure-password-here

.. envvar:: PLANKA_PROJECT_NAME

   Name of the project in Planka.
   
   :Default: ``PM Agent Project``
   :Auto-created: Yes, if doesn't exist
   
   Example::
   
      PLANKA_PROJECT_NAME=My Awesome Project

.. envvar:: PLANKA_SECRET_KEY

   Secret key for Planka (if configured).
   
   :Required: No
   :Use: Only if Planka requires it

Remote Deployment
-----------------

For remote/cloud deployment:

.. envvar:: MCP_AUTH_TOKENS

   Comma-separated list of authentication tokens.
   
   :Format: ``token1,token2,token3``
   :Use: Authenticate remote worker connections
   :Security: Use strong, unique tokens
   
   Example::
   
      MCP_AUTH_TOKENS=secret-token-1,secret-token-2

.. envvar:: HOST

   IP address to bind the server to.
   
   :Default: ``127.0.0.1`` (local only)
   :Remote: ``0.0.0.0`` (all interfaces)
   
   Example::
   
      HOST=0.0.0.0

.. envvar:: PORT

   Port number for PM Agent server.
   
   :Default: ``8000``
   :Range: 1024-65535
   
   Example::
   
      PORT=8080

Logging Configuration
---------------------

.. envvar:: LOG_LEVEL

   Controls verbosity of logging output.
   
   :Valid values: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``
   :Default: ``INFO``
   
   Example::
   
      LOG_LEVEL=DEBUG

.. envvar:: LOG_FILE

   Path to log file (optional).
   
   :Default: Logs to console only
   :Format: Absolute or relative path
   
   Example::
   
      LOG_FILE=/var/log/pm-agent.log

.. envvar:: LOG_FORMAT

   Log message format.
   
   :Default: ``%(asctime)s - %(name)s - %(levelname)s - %(message)s``
   :Use: Customize log output format

Development Variables
---------------------

.. envvar:: DEBUG

   Enable debug mode.
   
   :Valid values: ``true``, ``false``
   :Default: ``false``
   :Effects: More verbose output, debug endpoints
   
   Example::
   
      DEBUG=true

.. envvar:: RELOAD

   Auto-reload on code changes.
   
   :Valid values: ``true``, ``false``
   :Default: ``false``
   :Use: Development only
   
   Example::
   
      RELOAD=true

Docker Variables
----------------

Used in Docker deployment:

.. envvar:: DOCKER_BUILDKIT

   Enable Docker BuildKit.
   
   :Valid values: ``1``, ``0``
   :Default: ``1``
   :Benefits: Faster builds, better caching

.. envvar:: COMPOSE_PROJECT_NAME

   Docker Compose project name.
   
   :Default: ``pm-agent``
   :Use: Namespace containers

Proxy Configuration
-------------------

For environments behind proxies:

.. envvar:: HTTP_PROXY

   HTTP proxy server.
   
   :Format: ``http://proxy.example.com:8080``
   :Use: Route HTTP traffic through proxy

.. envvar:: HTTPS_PROXY

   HTTPS proxy server.
   
   :Format: ``http://proxy.example.com:8080``
   :Use: Route HTTPS traffic through proxy

.. envvar:: NO_PROXY

   Bypass proxy for these hosts.
   
   :Format: Comma-separated hostnames
   :Example: ``localhost,127.0.0.1,.local``

Example .env Files
------------------

Development (GitHub)
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Provider
   KANBAN_PROVIDER=github
   
   # GitHub
   GITHUB_TOKEN=ghp_your_token_here
   GITHUB_OWNER=your-username
   GITHUB_REPO=your-project
   
   # AI
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   
   # Logging
   LOG_LEVEL=INFO

Local Development (Planka)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Provider
   KANBAN_PROVIDER=planka
   
   # Planka (defaults work for local)
   PLANKA_BASE_URL=http://localhost:3333
   PLANKA_AGENT_EMAIL=demo@demo.demo
   PLANKA_AGENT_PASSWORD=demo
   
   # AI
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   
   # Development
   DEBUG=true
   LOG_LEVEL=DEBUG

Production (Linear)
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Provider
   KANBAN_PROVIDER=linear
   
   # Linear
   LINEAR_API_KEY=lin_api_production_key
   LINEAR_TEAM_ID=PROD-TEAM
   
   # AI
   ANTHROPIC_API_KEY=sk-ant-production-key
   
   # Security
   MCP_AUTH_TOKENS=prod-token-1,prod-token-2
   
   # Server
   HOST=0.0.0.0
   PORT=8443
   
   # Logging
   LOG_LEVEL=WARNING
   LOG_FILE=/var/log/pm-agent/production.log

Security Best Practices
-----------------------

1. **Never commit .env files**
   
   * Add to ``.gitignore``
   * Use ``.env.example`` as template

2. **Use strong tokens**
   
   * Generate random tokens
   * Rotate regularly
   * Different per environment

3. **Limit permissions**
   
   * GitHub tokens: minimal scopes
   * API keys: restricted usage

4. **Secure storage**
   
   * Use secrets management in production
   * Encrypt sensitive values
   * Audit access logs

5. **Environment isolation**
   
   * Separate keys per environment
   * Don't reuse development keys
   * Monitor usage

Loading Order
-------------

PM Agent loads configuration in this order:

1. System environment variables
2. ``.env`` file in project root
3. ``config_pm_agent.json`` for project settings
4. Command-line arguments (if applicable)

Later sources override earlier ones.

Validation
----------

PM Agent validates configuration on startup:

* Required variables present
* Format validation
* Connection testing
* Permission checking

Missing required variables cause startup failure with helpful error messages.