# Marcus Configuration Guide

## Quick Start

1. Copy the example configuration file:
   ```bash
   cp config_marcus.example.json config_marcus.json
   ```

2. Edit `config_marcus.json` with your settings:
   - **Planka credentials** - for your kanban board
   - **Anthropic API key** - for AI features
   - **GitHub/Linear credentials** - if using those providers

## Configuration File: config_marcus.json

All configuration is stored in a single file: `config_marcus.json`

This file contains:
- Kanban board settings (Planka, GitHub, Linear)
- API keys (Anthropic for AI features)
- Project and board IDs

### Example Structure

```json
{
  "project_id": "your_project_id",
  "board_id": "your_board_id", 
  "project_name": "Your Project Name",
  "auto_find_board": false,
  
  "kanban": {
    "provider": "planka"
  },
  
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "your_email@example.com",
    "password": "your_password"
  },
  
  "ai": {
    "anthropic_api_key": "sk-ant-your-key-here",
    "model": "claude-3-sonnet-20240229"
  },
  
  "github": {
    "token": "ghp_your_token",
    "owner": "your_username",
    "repo": "your_repo"
  },
  
  "linear": {
    "api_key": "lin_api_your_key",
    "team_id": "your_team_id"
  }
}
```

## Security

- `config_marcus.json` is in `.gitignore` - it will NOT be committed to git
- Never commit your API keys or passwords
- Use `config_marcus.example.json` as a template for sharing

## Legacy Files

The following files are deprecated and will be removed in future versions:
- `.env` - Configuration now in config_marcus.json
- `marcus.config.json` - Renamed to config_marcus.json

## Provider-Specific Setup

### Planka (Default)
1. Install Planka locally or use a hosted instance
2. Create a project and board
3. Copy the project_id and board_id to config_marcus.json

### GitHub Projects
1. Create a GitHub personal access token with `project` scope
2. Note your repository owner and name
3. Fill in the github section

### Linear
1. Get your Linear API key from settings
2. Find your team ID
3. Fill in the linear section