# 🖼️ PM Agent Setup - Visual Guide

This guide shows you exactly what to click and type, step by step!

## 📱 Setting Up with Claude Desktop

### Step 1: Find Claude Desktop Settings

#### On Windows:
1. Open Claude Desktop
2. Click the **menu button** (three lines ☰) in top-left corner
3. Click **Settings**
4. Click **Developer** on the left side
5. Click **Edit Config**

![Windows Settings Location]
```
┌─────────────────────────────────┐
│ ☰ Claude Desktop                │
├─────────────────────────────────┤
│ 📝 New Conversation             │
│ ⚙️ Settings         <-- Click   │
│ ❓ Help                         │
└─────────────────────────────────┘
```

#### On Mac:
1. Open Claude Desktop
2. Click **Claude Desktop** in the menu bar (top of screen)
3. Click **Preferences** (or press ⌘+,)
4. Click **Developer** tab
5. Click **Edit Config**

![Mac Settings Location]
```
┌─────────────────────────────────┐
│ Claude Desktop  File  Edit      │
├─────────────────────────────────┤
│ About Claude Desktop            │
│ Preferences...    <-- Click     │
│ Quit Claude Desktop             │
└─────────────────────────────────┘
```

### Step 2: The Config File Opens

You'll see something like this:
```json
{
  "mcpServers": {
    
  }
}
```

Or it might be empty - that's OK!

### Step 3: Copy the Right Template

#### If You're on Windows:
Copy this entire block:
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "python",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "C:\\Users\\YOUR_NAME\\pm-agent"
    }
  }
}
```

⚠️ **IMPORTANT**: Change `YOUR_NAME` to your actual Windows username!

#### If You're on Mac:
Copy this entire block:
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

⚠️ **IMPORTANT**: Change `YOUR_NAME` to your actual Mac username!

### Step 4: Paste and Save

1. Select ALL text in the config file (Ctrl+A on Windows, Cmd+A on Mac)
2. Paste the template (Ctrl+V on Windows, Cmd+V on Mac)
3. Change `YOUR_NAME` to your username
4. Save the file (Ctrl+S on Windows, Cmd+S on Mac)
5. Close the editor

### Step 5: Restart Claude Desktop

1. Close Claude Desktop completely
   - Windows: Click X button, or right-click taskbar icon → Quit
   - Mac: Cmd+Q, or Claude Desktop menu → Quit
2. Wait 5 seconds
3. Open Claude Desktop again

### Step 6: Test It!

Type this in Claude Desktop:
```
Can you use the pm-agent ping tool?
```

✅ **Success looks like:**
```
I'll check if the PM Agent is running using the ping tool.

Status: online
Service: PM Agent MVP
Health: healthy
```

❌ **If it didn't work:**
```
I don't have access to a tool called "pm-agent"
```

## 🖥️ Setting Up with Claude Code

### Step 1: Open Terminal/Command Prompt

#### Windows:
1. Press `Windows` key
2. Type: `cmd`
3. Press Enter

![Windows Terminal]
```
┌─────────────────────────────────┐
│ C:\Users\YourName>              │
│ _                               │
│                                 │
│                                 │
└─────────────────────────────────┘
```

#### Mac:
1. Press `Cmd + Space`
2. Type: `terminal`
3. Press Enter

![Mac Terminal]
```
┌─────────────────────────────────┐
│ YourName@MacBook ~ %            │
│ _                               │
│                                 │
│                                 │
└─────────────────────────────────┘
```

### Step 2: Type The Magic Command

Type this exactly (all on one line):

**Windows:**
```
claude mcp add pm-agent python -m src.pm_agent_mvp_fixed
```

**Mac:**
```
claude mcp add pm-agent python3 -m src.pm_agent_mvp_fixed
```

Press Enter!

### Step 3: You Should See

✅ **Success:**
```
Successfully added MCP server 'pm-agent'
```

❌ **If you see "command not found":**
- Make sure Claude Code is installed
- Try restarting your computer

### Step 4: Test in Claude Code

Open Claude Code and type:
```
Use the pm-agent ping tool
```

## 🚨 Troubleshooting Picture Guide

### Problem: "Python not found"

![Python Not Found Error]
```
'python' is not recognized as an internal or external command
```

**Fix:** You need to install Python!
1. Go to [python.org](https://python.org)
2. Click the big yellow "Download Python" button
3. Run the installer
4. ⚠️ **IMPORTANT**: Check this box:
   ```
   ☑ Add Python to PATH
   ```

### Problem: "No module named src"

![Module Not Found Error]
```
ModuleNotFoundError: No module named 'src'
```

**Fix:** PM Agent isn't in the right place!

The folder structure should look like:
```
pm-agent/
├── src/
│   ├── pm_agent_mvp_fixed.py
│   └── (other files)
├── config_pm_agent.json
└── requirements.txt
```

### Problem: Config File Has Errors

![JSON Error]
```
Failed to parse config file: Unexpected token
```

**Fix:** You have a typo! Common mistakes:
- Missing comma
- Wrong type of quotes (use " not ')
- Extra bracket

Use this tool to check: [jsonlint.com](https://jsonlint.com)

## 📍 Quick Reference Card

Save this for later!

### Your Paths Cheat Sheet

Fill these in once you know them:

**My Python Path:** _______________________
- Find it with: `where python` (Windows) or `which python3` (Mac)

**My PM Agent Path:** _______________________
- Where you saved the PM Agent folder

**My Username:** _______________________
- Your computer username

### The Config Template

Keep this handy:
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "[YOUR_PYTHON_PATH]",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "[YOUR_PM_AGENT_PATH]"
    }
  }
}
```

## 🎉 Success Checklist

- [ ] Found config file location
- [ ] Found Python path
- [ ] Found PM Agent folder
- [ ] Edited config file
- [ ] Saved config file
- [ ] Restarted Claude
- [ ] Tested with ping command
- [ ] Got "Status: online" response

All checked? You're ready to use PM Agent! 🚀