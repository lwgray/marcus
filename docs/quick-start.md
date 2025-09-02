# Quick Start Guide

Get Marcus running in 5 minutes.

## Prerequisites

- Docker
- GitHub account with [personal access token](https://github.com/settings/tokens) (needs `project` scope)
- AI API key (Anthropic, OpenAI, or local Ollama)
- Claude Code or another MCP-compatible agent

## Step 1: Get Your Tokens

1. **GitHub Token**: Go to [GitHub Settings > Tokens](https://github.com/settings/tokens)
   - Click "Generate new token (classic)"
   - Select scope: `project` (Full control of projects)
   - Copy the token (starts with `ghp_`)

2. **AI API Key**: Choose one:
   - [Anthropic Console](https://console.anthropic.com/) for Claude
   - [OpenAI Platform](https://platform.openai.com/) for GPT
   - Or run Ollama locally (no key needed)

## Step 2: Run Marcus

```bash
# Quick start with environment variables
docker run -p 4298:4298 \
  -e GITHUB_TOKEN=ghp_your_token_here \
  -e ANTHROPIC_API_KEY=sk-ant-your_key_here \
  marcus/marcus:latest
```

Or build from source:

```bash
git clone https://github.com/lwgray/marcus.git
cd marcus
docker build -t marcus .
docker run -p 4298:4298 \
  -e GITHUB_TOKEN=ghp_your_token \
  -e ANTHROPIC_API_KEY=sk-ant-your_key \
  marcus
```

## Step 3: Connect Your Agent

In Claude Code:
```bash
claude mcp add http://localhost:4298/marcus
```

For other agents, connect to `http://localhost:4298/marcus` as an MCP server.

## Step 4: Configure Agent Workflow

Copy the contents of [prompts/Agent_prompt.md](../prompts/Agent_prompt.md) as your agent's system prompt.

This gives your agent:
- The complete Marcus workflow
- Automatic task management
- Context sharing capabilities
- Error recovery

## Step 5: Start Building!

Tell your agent:
```
Create a project for a todo app with authentication using Marcus and start working
```

You'll see:
1. Agent registers with Marcus
2. Project created on GitHub
3. Tasks automatically generated
4. Agent working through tasks
5. Progress updates in real-time

## What's Next?

- **Add more agents**: Open another terminal and connect another agent
- **Monitor progress**: Check your GitHub project board
- **Customize**: See [Configuration Guide](configuration.md)
- **Learn more**: Read [Agent Workflow](agent-workflow.md)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check Marcus is running on port 4298 |
| GitHub auth failed | Verify token has `project` scope |
| No tasks available | Agent needs to create project first |
| Agent not working | Ensure you set the system prompt |

Need help? Join our [Discord](https://discord.gg/marcus) or check [GitHub Issues](https://github.com/lwgray/marcus/issues).