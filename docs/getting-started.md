# 🚀 Getting Started with PM Agent

Welcome! This guide will help you set up PM Agent in about 5 minutes.

## 📝 What You'll Need

Before starting, make sure you have:

1. **A computer** with either Windows, Mac, or Linux
2. **Docker Desktop** installed ([Download here](https://www.docker.com/products/docker-desktop))
3. **A GitHub account** (free at [github.com](https://github.com))
4. **An AI API key** from Anthropic ([Get one here](https://console.anthropic.com))

## 🎯 Step 1: Download PM Agent

Open your terminal (Command Prompt on Windows, Terminal on Mac) and type:

```bash
git clone https://github.com/your-username/pm-agent.git
cd pm-agent
```

This downloads PM Agent to your computer.

## 🔧 Step 2: Start PM Agent

Just run this command:

```bash
./start.sh
```

This will:
- Create a settings file (`.env`)
- Start PM Agent in Docker
- Set everything up automatically

## 🔑 Step 3: Add Your API Keys

PM Agent needs some "passwords" (API keys) to work. Open the `.env` file in any text editor:

```bash
# On Mac/Linux
nano .env

# On Windows
notepad .env
```

You'll see something like this:

```
# Kanban Provider (github, linear, or planka)
KANBAN_PROVIDER=github

# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
GITHUB_OWNER=your_github_username
GITHUB_REPO=your_repo_name

# AI Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Getting Your Keys:

1. **GitHub Token**:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token"
   - Give it a name like "PM Agent"
   - Select these permissions: `repo`, `project`
   - Copy the token and paste it in `.env`

2. **Anthropic API Key**:
   - Go to https://console.anthropic.com
   - Find your API key
   - Copy and paste it in `.env`

3. **Your GitHub Info**:
   - `GITHUB_OWNER`: Your GitHub username
   - `GITHUB_REPO`: Name of a repository you want to use

Save the file when done!

## 🔄 Step 4: Restart PM Agent

After adding your keys, restart PM Agent:

```bash
docker-compose restart
```

## ✅ Step 5: You're Done!

PM Agent is now running! Here's what happens next:

1. **AI workers can connect** and ask for tasks
2. **Tasks come from GitHub Issues** in your repository
3. **PM Agent assigns tasks** based on what workers are good at
4. **Progress is tracked** automatically

## 🎮 Try It Out!

Want to see PM Agent in action? Run the demo:

```bash
./start.sh demo
```

This starts PM Agent with 3 pretend workers who will:
- Ask for tasks
- Work on them
- Report progress
- Complete them

## 🚫 Common Problems

### "Docker not found"
→ Install Docker Desktop first

### "Permission denied"  
→ On Mac/Linux, run: `chmod +x start.sh`

### "Invalid API key"
→ Double-check your keys in `.env` file

### "Cannot connect to Docker"
→ Make sure Docker Desktop is running

## 🎯 Next Steps

1. **Create some tasks** - Add issues to your GitHub repository
2. **Watch it work** - See PM Agent assign tasks to workers
3. **Check the logs** - Look in `logs/` folder to see conversations

## 💡 Tips for Beginners

- Start with just a few simple tasks
- Use clear task titles like "Create login page" or "Add user database"
- Check the logs to understand what's happening
- Don't worry if something breaks - just restart!

## 🆘 Still Stuck?

- Read the [Troubleshooting Guide](troubleshooting.md)
- Check [Common Questions](faq.md)
- Ask for help on GitHub Issues

---

Ready to dive deeper? Check out [How It Works](how-it-works.md) to understand PM Agent better!