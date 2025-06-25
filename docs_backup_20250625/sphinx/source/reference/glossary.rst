Glossary
========

Common terms and concepts used in PM Agent documentation.

.. glossary::
   :sorted:

   Agent
      An AI worker that connects to PM Agent to complete tasks. Agents have specific skills and roles.

   API Key
      Authentication credential for external services like Anthropic (for AI) or GitHub (for issues).

   Assignment
      The process of matching a task to a worker agent based on skills, priority, and availability.

   Backlog
      Collection of tasks that haven't been started yet. In kanban boards, this is typically the first column.

   Blocker
      An issue preventing a worker from completing a task. PM Agent provides AI-powered resolution suggestions.

   Board
      Visual representation of project tasks, typically with columns like Backlog, In Progress, and Done.

   Board ID
      Unique identifier for a specific kanban board within a project.

   Claude
      Anthropic's AI assistant, commonly used as a worker agent with PM Agent.

   Column
      A vertical section of a kanban board representing a task state (e.g., Todo, In Progress, Done).

   Conversation Log
      Detailed record of communications between workers, PM Agent, and the kanban board.

   Docker
      Container platform used to package and run PM Agent and its dependencies.

   Docker Compose
      Tool for defining and running multi-container Docker applications, used for PM Agent deployment.

   Environment Variables
      Configuration values set outside the application, typically in a .env file.

   Kanban
      Project management method using visual boards to track work progress.

   Label
      Tag attached to tasks to indicate type, priority, or required skills (e.g., "backend", "urgent").

   Linear
      Cloud-based project management tool that PM Agent can integrate with.

   MCP
      Model Context Protocol - Standard for AI model communication used by PM Agent.

   MCP Client
      Component that connects to an MCP server to use its tools (PM Agent connects to kanban-mcp).

   MCP Server
      Component that exposes tools via MCP (PM Agent acts as server for worker agents).

   MCP Tool
      Specific function exposed via MCP that agents can call (e.g., register_agent, request_next_task).

   Planka
      Open-source kanban board that runs locally, used as default task board for PM Agent.

   PM Agent
      The AI-powered project manager that coordinates autonomous software development teams.

   Priority
      Importance level of a task (Urgent, High, Medium, Low) used for assignment decisions.

   Progress
      Percentage completion of a task, reported by workers during execution.

   Project ID
      Unique identifier for a project containing multiple boards and tasks.

   Provider
      Task management system PM Agent integrates with (GitHub, Linear, or Planka).

   Registration
      Process where a worker agent declares its identity and capabilities to PM Agent.

   Skill
      Technical capability of a worker (e.g., "python", "react", "docker") used for task matching.

   Sphinx
      Documentation generator used to create PM Agent's documentation from RST and Markdown files.

   Task
      Unit of work to be completed, with title, description, labels, and success criteria.

   Task Assignment
      Matching a task to a worker based on skills, priority, and availability.

   Task ID
      Unique identifier for a specific task or card on the kanban board.

   Visualization
      Real-time graphical display of PM Agent's operation, showing data flow and decisions.

   WebSocket
      Protocol enabling real-time bidirectional communication, used for live updates.

   Worker
      AI agent that performs actual development work on assigned tasks.

   Worker Agent
      Same as Worker - an autonomous AI that completes software development tasks.

   Worker ID
      Unique identifier for a specific worker agent instance.

   Worker Status
      Current state of a worker including assigned tasks, completed count, and availability.

   Workspace
      Isolated directory where a worker agent performs its tasks, with security boundaries.

   Workspace Manager
      Component that assigns and manages secure workspaces for each worker agent.