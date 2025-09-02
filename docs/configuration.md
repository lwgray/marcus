# Marcus Configuration Guide

## Configuration Methods

Marcus can be configured using either environment variables or a configuration file.

### Environment Variables

The easiest way to configure Marcus, especially when using Docker:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx        # GitHub personal access token
export ANTHROPIC_API_KEY=sk-ant-xxxxx       # For Claude models
export OPENAI_API_KEY=sk-xxxxx              # For GPT models (optional)
export KANBAN_PROVIDER=github               # Kanban board provider
```

### Configuration File

Create a `config_marcus.json` file based on `config_marcus.example.json`:

```json
{
  "github_token": "ghp_xxxxxxxxxxxxx",
  "anthropic_api_key": "sk-ant-xxxxx",
  "kanban_provider": "github",
  "context_dependency": true,
  "ai_provider": "anthropic",
  "model": "claude-3-5-sonnet-20241022"
}
```

## Configuration Options

| Option | Description | Default | Required |
|--------|-------------|---------|----------|
| `github_token` | GitHub personal access token with `project` scope | - | Yes |
| `anthropic_api_key` | Anthropic API key for Claude models | - | Yes* |
| `openai_api_key` | OpenAI API key for GPT models | - | Yes* |
| `kanban_provider` | Board provider: `github`, `linear`, `planka` | `github` | No |
| `context_dependency` | Enable context sharing between tasks | `true` | No |
| `ai_provider` | AI provider: `anthropic`, `openai`, `ollama` | `anthropic` | No |
| `model` | Model name to use | Provider default | No |

*One AI provider key is required

## Provider-Specific Configuration

### GitHub Projects
```json
{
  "kanban_provider": "github",
  "github_token": "ghp_xxxxxxxxxxxxx",
  "github_org": "your-org",  // Optional
  "github_repo": "your-repo" // Optional
}
```

### Local Models with Ollama
```json
{
  "ai_provider": "ollama",
  "ollama_base_url": "http://localhost:11434",
  "model": "llama2"
}
```

See [Setup Local LLM Guide](user-guide/how-to/setup-local-llm.md) for details.

## Docker Configuration

When using Docker, mount your config file:

```bash
docker run -p 4298:4298 \
  -v $(pwd)/config_marcus.json:/app/config_marcus.json \
  marcus/marcus:latest
```

Or use environment variables:

```bash
docker run -p 4298:4298 \
  -e GITHUB_TOKEN=ghp_xxxxx \
  -e ANTHROPIC_API_KEY=sk-ant-xxxxx \
  marcus/marcus:latest
```