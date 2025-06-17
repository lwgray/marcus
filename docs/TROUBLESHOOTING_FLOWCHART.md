# 🔧 PM Agent Troubleshooting Flowchart

Follow this step-by-step guide to fix any setup issues!

## Start Here ↓

### Did Claude Desktop/Code start without errors?
- **YES** → Go to [Test PM Agent](#test-pm-agent)
- **NO** → Go to [Claude Won't Start](#claude-wont-start)

---

## Test PM Agent

### In Claude, type: "Can you use the pm-agent ping tool?"

**What happened?**

#### ✅ "Status: online"
**Congratulations! PM Agent is working!** 🎉

#### ❌ "I don't have access to a tool called pm-agent"
→ Go to [PM Agent Not Found](#pm-agent-not-found)

#### ❌ "MCP server failed to start"
→ Go to [Server Start Failed](#server-start-failed)

#### ❌ "Board ID not set"
→ Go to [Configuration Missing](#configuration-missing)

---

## PM Agent Not Found

Claude can't see PM Agent. Let's fix this!

### For Claude Desktop:

1. **Did you edit the config file?**
   - NO → Go back to [EASY_SETUP.md](../EASY_SETUP.md#step-4-edit-the-config-file)
   - YES → Continue ↓

2. **Did you restart Claude Desktop completely?**
   - NO → Quit Claude Desktop fully (not just minimize), wait 5 seconds, open again
   - YES → Continue ↓

3. **Check your config file for typos:**
   ```json
   {
     "mcpServers": {
       "pm-agent": {
         ← Make sure this says exactly "pm-agent"
   ```

### For Claude Code:

1. **Run this command again:**
   ```
   claude mcp add pm-agent python3 -m src.pm_agent_mvp_fixed
   ```

2. **What did it say?**
   - "Successfully added" → Restart Claude Code and try again
   - "Error" → Continue to [Server Start Failed](#server-start-failed)

---

## Server Start Failed

PM Agent can't start. Let's diagnose!

### Step 1: Test Python

Open terminal/command prompt and type:
```
python --version
```
or
```
python3 --version
```

**What happened?**
- Shows version (like "Python 3.9.0") → Go to Step 2
- "command not found" → [Install Python](#install-python)

### Step 2: Test PM Agent Directory

1. In terminal, go to PM Agent folder:
   ```
   cd /path/to/pm-agent
   ```

2. List files:
   ```
   ls
   ```
   (Windows: use `dir`)

**Do you see these files?**
- `src/` (folder)
- `requirements.txt`
- `config_pm_agent.json`

- YES → Go to Step 3
- NO → You're in wrong folder! Find where you saved PM Agent

### Step 3: Test PM Agent Directly

Run this command:
```
python -m src.pm_agent_mvp_fixed
```
(Mac/Linux: use `python3`)

**What happened?**
- "PM Agent MVP is ready!" → [Fix Config Path](#fix-config-path)
- "No module named..." → [Install Dependencies](#install-dependencies)
- Other error → [Check Error Messages](#check-error-messages)

---

## Configuration Missing

### Create config_pm_agent.json

1. Go to PM Agent folder
2. Create new file called `config_pm_agent.json`
3. Put this in it:
   ```json
   {
     "project_id": "1234567890",
     "board_id": "0987654321"
   }
   ```
4. Save the file
5. Try PM Agent again

---

## Claude Won't Start

### For Claude Desktop:

1. **Check if config file has errors:**
   - Copy your config file content
   - Go to [jsonlint.com](https://jsonlint.com)
   - Paste and click "Validate"
   - Fix any errors shown

2. **Common JSON errors:**
   ```json
   {
     "mcpServers": {
       "pm-agent": {
         "command": "python",      ← Need comma here!
         "args": ["-m", "src.pm_agent_mvp_fixed"],
         "cwd": "C:\path"          ← Use \\ or / for Windows paths!
       }
     }
   }
   ```

---

## Fix Config Path

Your config file has wrong paths. Let's fix them!

### Find Correct Paths:

1. **Find Python path:**
   ```
   which python3
   ```
   (Windows: `where python`)

2. **Find PM Agent path:**
   ```
   pwd
   ```
   (Shows current directory - make sure you're in pm-agent folder)

3. **Update config file with these exact paths**

### Common Path Mistakes:

❌ **Wrong:**
```json
"command": "python",
"cwd": "~/pm-agent"     ← ~ doesn't work in JSON!
```

✅ **Right:**
```json
"command": "/usr/bin/python3",
"cwd": "/Users/yourname/pm-agent"
```

❌ **Wrong (Windows):**
```json
"cwd": "C:\Users\Name\pm-agent"    ← Single \ breaks JSON!
```

✅ **Right (Windows):**
```json
"cwd": "C:\\Users\\Name\\pm-agent"  ← Double \\
```
or
```json
"cwd": "C:/Users/Name/pm-agent"     ← Forward /
```

---

## Install Python

### Windows:
1. Go to [python.org](https://python.org)
2. Click "Download Python 3.x.x"
3. Run installer
4. ⚠️ **CHECK THIS BOX:** "Add Python to PATH"
5. Click "Install Now"
6. Restart your computer

### Mac:
1. Open Terminal
2. Install Homebrew first:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Install Python:
   ```
   brew install python3
   ```

### Linux:
```
sudo apt update
sudo apt install python3 python3-pip
```

---

## Install Dependencies

PM Agent needs some extra files to work.

1. Go to PM Agent folder:
   ```
   cd /path/to/pm-agent
   ```

2. Install requirements:
   ```
   pip install -r requirements.txt
   ```
   (Mac/Linux: `pip3 install -r requirements.txt`)

**Errors?**
- "pip not found" → Try `python -m pip install -r requirements.txt`
- "Permission denied" → Mac/Linux: add `sudo` before the command
- Still not working → [Get Help](#get-help)

---

## Check Error Messages

### Common Errors:

**"ImportError: No module named anthropic"**
- Run: `pip install anthropic`

**"ConnectionRefusedError"**
- Planka isn't running
- Start it with: `cd /path/to/kanban-mcp && npm run up`

**"PermissionError"**
- Windows: Run as Administrator
- Mac/Linux: Use `sudo` before commands

---

## Get Help

Still stuck? Here's how to get help:

### 1. Gather Information:
- Screenshot of the error
- Your operating system (Windows/Mac/Linux)
- Python version (`python --version`)
- What step you're on

### 2. Check These First:
- Is Python installed?
- Is PM Agent in the right folder?
- Did you restart Claude after changes?
- Are all paths spelled correctly?

### 3. Common Quick Fixes:
- Restart your computer
- Re-download PM Agent
- Try `python3` instead of `python`
- Check file permissions

### 4. Still Need Help?
Create an issue with:
- Error message (full text)
- Your config file (remove any passwords)
- Steps you've tried

Remember: Everyone gets stuck sometimes. You're doing great! 🌟