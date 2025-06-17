# 📋 PM Agent Quick Reference Card

Print this page and keep it handy!

## 🚀 Setup in 30 Seconds

### Claude Desktop
1. Find config: `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/` (Mac)
2. Paste this (change YOUR_NAME):
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "python3",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/Users/YOUR_NAME/pm-agent"
    }
  }
}
```
3. Save, restart Claude Desktop
4. Test: "Can you use the pm-agent ping tool?"

### Claude Code
```bash
claude mcp add pm-agent python3 -m src.pm_agent_mvp_fixed
```

## 🔍 Find Your Paths

| What | Command | Example Result |
|------|---------|----------------|
| Python | `which python3` | `/usr/bin/python3` |
| Current folder | `pwd` | `/Users/name/pm-agent` |
| Windows Python | `where python` | `C:\Python39\python.exe` |

## ✅ Test Commands

In Claude, try these:
- `Use the pm-agent ping tool` - Check if connected
- `Use pm-agent get_project_status` - See project info
- `Use pm-agent list_registered_agents` - See all agents

## 🛠️ Common Fixes

| Problem | Solution |
|---------|----------|
| "Python not found" | Install from python.org |
| "No module named src" | Wrong folder - cd to pm-agent |
| "MCP server failed" | Check paths in config |
| Config errors | Use forward slashes `/` or double backslash `\\` |
| Nothing happens | Fully restart Claude (quit, not minimize) |

## 📁 Required Files

Your pm-agent folder needs:
```
pm-agent/
├── src/
│   └── pm_agent_mvp_fixed.py
├── config_pm_agent.json
└── requirements.txt
```

## 🎯 Windows Config Example
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "C:\\Python39\\python.exe",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "C:\\Users\\John\\pm-agent"
    }
  }
}
```

## 🎯 Mac Config Example
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "/usr/bin/python3",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/Users/john/pm-agent"
    }
  }
}
```

## 🚨 Emergency Checklist

- [ ] Python installed? (`python --version`)
- [ ] In pm-agent folder? (`pwd`)
- [ ] Config file saved?
- [ ] Claude restarted completely?
- [ ] Used correct path separators?
- [ ] No typos in "pm-agent"?

## 📞 Still Stuck?

1. Take screenshot of error
2. Note your OS (Windows/Mac/Linux)
3. Try [Visual Guide](docs/SETUP_WITH_PICTURES.md)
4. Check [Troubleshooting](docs/TROUBLESHOOTING_FLOWCHART.md)

---
*Keep this page handy during setup!* 🌟