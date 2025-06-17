# 🚀 Super Easy PM Agent Setup

This guide will help you set up PM Agent in 5 minutes or less! No technical knowledge required.

> **🖼️ Want pictures?** Check out our [Visual Setup Guide](docs/SETUP_WITH_PICTURES.md) with screenshots!

## 📋 What You Need First

Before starting, make sure you have:
1. ✅ Python installed on your computer
2. ✅ Downloaded PM Agent files
3. ✅ Claude Desktop or Claude Code installed

## 🎯 Quick Setup for Claude Desktop

### Step 1: Find Your Setup File

First, we need to find where Claude Desktop keeps its settings:

**On Windows:**
1. Press `Windows + R` keys together
2. Type: `%APPDATA%\Claude`
3. Press Enter
4. Look for a file called `claude_desktop_config.json`

**Can't find it?** The file might not exist yet. Create a new file:
1. Right-click in the folder
2. Select New > Text Document
3. Name it exactly: `claude_desktop_config.json`
4. Make sure to remove the `.txt` at the end!

**On Mac:**
1. Open Finder
2. Press `Cmd + Shift + G`
3. Paste: `~/Library/Application Support/Claude/`
4. Press Enter
5. Look for a file called `claude_desktop_config.json`

**Can't find it?** The file might not exist yet. Create it:
1. Open TextEdit
2. Click Format > Make Plain Text
3. Save as: `claude_desktop_config.json` in that folder

**On Linux:**
1. Open your file manager
2. Press `Ctrl + H` to show hidden files
3. Go to: `.config/Claude/`
4. Look for a file called `claude_desktop_config.json`

### Step 2: Find Your Python

**What's Python?** It's what makes PM Agent work. Let's find where it lives on your computer!

Open a terminal/command prompt and type:

**Windows:** Open Command Prompt and type:
```
where python
```

**Mac/Linux:** Open Terminal and type:
```
which python3
```

Write down the path it shows you. It will look something like:
- Windows: `C:\Python39\python.exe` or `C:\Users\YourName\AppData\Local\Programs\Python\Python39\python.exe`
- Mac: `/usr/bin/python3` or `/usr/local/bin/python3`
- Linux: `/usr/bin/python3`

**Didn't work?** You might need to [install Python first](#python-not-found)!

### Step 3: Find PM Agent Folder

Remember where you saved/downloaded PM Agent. The path might look like:
- Windows: `C:\Users\YourName\pm-agent`
- Mac: `/Users/YourName/pm-agent`
- Linux: `/home/yourname/pm-agent`

### Step 4: Edit the Config File

1. Open `claude_desktop_config.json` in Notepad (Windows) or TextEdit (Mac)
2. Replace everything in the file with this:

```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "YOUR_PYTHON_PATH",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "YOUR_PM_AGENT_PATH"
    }
  }
}
```

3. Replace `YOUR_PYTHON_PATH` with the path from Step 2
4. Replace `YOUR_PM_AGENT_PATH` with the path from Step 3

**Real Example (Windows):**
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

**Real Example (Mac):**
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

### Step 5: Save and Restart

1. Save the file
2. Completely close Claude Desktop (not just minimize)
3. Open Claude Desktop again

### Step 6: Test It Works

In Claude Desktop, type:
```
Can you use the pm-agent ping tool?
```

If it works, you'll see a response with "Status: online" 🎉

## 🎯 Quick Setup for Claude Code

### Step 1: Open Terminal

- **Windows:** Open Command Prompt
- **Mac:** Open Terminal (find it in Applications > Utilities)
- **Linux:** Open Terminal (Ctrl+Alt+T)

### Step 2: Run One Command

Type this command, but replace the paths:

```
claude mcp add pm-agent YOUR_PYTHON_PATH -m src.pm_agent_mvp_fixed
```

**Examples:**

Windows:
```
claude mcp add pm-agent C:\Python39\python.exe -m src.pm_agent_mvp_fixed
```

Mac/Linux:
```
claude mcp add pm-agent python3 -m src.pm_agent_mvp_fixed
```

### Step 3: Test It

In Claude Code, type:
```
Use the pm-agent ping tool
```

## ❓ Common Problems & Solutions

### "Python not found"

**Solution:** You need to install Python first
1. Go to [python.org](https://python.org)
2. Download Python
3. Install it (check "Add to PATH" during installation)

### "No module named src"

**Solution:** You're not in the right folder
1. In terminal, type: `cd YOUR_PM_AGENT_PATH`
2. Try the command again

### "Board ID not set"

**Solution:** PM Agent needs configuration
1. Create a file called `config_pm_agent.json` in the PM Agent folder
2. Put this in it:
```json
{
  "project_id": "test-project",
  "board_id": "test-board"
}
```

### Claude Desktop: "MCP server failed to start"

**Solution:** Your paths might have typos
- Make sure you used quotes around paths with spaces
- On Windows, use double backslashes `\\` or single forward slashes `/`

## 🎈 Even Easier: Copy-Paste Templates

### For Windows Users

1. Copy this template:
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "python",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "C:/Users/YOUR_USERNAME/pm-agent"
    }
  }
}
```

2. Just change `YOUR_USERNAME` to your Windows username

### For Mac Users

1. Copy this template:
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "python3",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/Users/YOUR_USERNAME/pm-agent"
    }
  }
}
```

2. Just change `YOUR_USERNAME` to your Mac username

## 🎉 You're Done!

Once PM Agent is connected, you can:
- Ask it to manage your tasks
- Get help when you're stuck
- Track your project progress

Just talk to Claude like normal, and it will use PM Agent to help you!

## 🆘 Still Need Help?

If you're stuck:
1. Take a screenshot of any error messages
2. Note which step you're on
3. Ask for help with the specific error

Remember: Everyone was a beginner once. You've got this! 🌟