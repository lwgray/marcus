# 📋 Choosing Your Task Board

PM Agent needs a place to get tasks from - like choosing between different brands of notebooks for your homework!

## 🎯 Quick Comparison

| Feature | GitHub | Linear | Planka |
|---------|--------|--------|---------|
| **Best For** | Most people | Companies | Personal use |
| **Cost** | Free! | $8/user/month | Free |
| **Setup Time** | 2 minutes | 3 minutes | 5 minutes |
| **Can Host Online?** | ✅ Yes | ✅ Yes | ❌ No |
| **Difficulty** | Easy | Easy | Medium |

## 🐙 GitHub Issues (Recommended!)

**What is it?** The task tracker built into GitHub

### ✅ Pros:
- Totally free
- Works with your code
- Super smart features (knows what code was written!)
- Used by millions
- Great for beginners

### ❌ Cons:
- Need a GitHub account
- Tasks mixed with code stuff

### 📝 Perfect if you:
- Are just starting out
- Want something free
- Like everything in one place
- Want to share your project

### 🚀 How to Set Up:
1. Create a GitHub repository
2. Get a token from GitHub settings
3. Add to your `.env` file:
```
KANBAN_PROVIDER=github
GITHUB_TOKEN=your_token_here
GITHUB_OWNER=your_username
GITHUB_REPO=your_repo_name
```

## 📊 Linear (For Teams)

**What is it?** A professional task tracker for companies

### ✅ Pros:
- Beautiful interface
- Fast and smooth
- Great for teams
- Professional features

### ❌ Cons:
- Costs money ($8/person/month)
- Overkill for personal projects
- Another account to manage

### 📝 Perfect if you:
- Work in a company
- Need professional features
- Have budget for tools
- Want the best UI

### 🚀 How to Set Up:
1. Sign up at linear.app
2. Get API key from settings
3. Add to your `.env` file:
```
KANBAN_PROVIDER=linear
LINEAR_API_KEY=your_key_here
LINEAR_TEAM_ID=your_team_id
```

## 🏠 Planka (Local Only!)

**What is it?** A self-hosted task board (runs on your computer)

### ✅ Pros:
- Free forever
- All data stays on your computer
- Simple and clean
- No accounts needed

### ❌ Cons:
- Can't use online (legal reasons)
- More complex setup
- No built-in backups
- Only for personal use

### ⚠️ Important Warning:
Planka has special licensing that means you can ONLY use it on your own computer. Never put it online!

### 📝 Perfect if you:
- Want everything local
- Don't need online access
- Like privacy
- Are just experimenting

### 🚀 How to Set Up:
1. Run special command:
```bash
./start.sh local-planka
```
2. Add to your `.env` file:
```
KANBAN_PROVIDER=planka
PLANKA_PROJECT_NAME=my-project
```

## 🤔 Which Should I Choose?

### Choose GitHub if:
- ✅ You're new to PM Agent
- ✅ You want free
- ✅ You might host online
- ✅ You want smart features

### Choose Linear if:
- ✅ You're in a company
- ✅ You can pay $8/month
- ✅ You want the best UI
- ✅ You need pro features

### Choose Planka if:
- ✅ You only work locally
- ✅ You want total privacy
- ✅ You never need online access
- ✅ You understand the licensing

## 🔄 Can I Switch Later?

Yes, but it's manual work:
1. Export your tasks from old system
2. Import into new system
3. Update your `.env` file
4. Restart PM Agent

## 💡 Pro Tip

Start with GitHub! It's:
- Free
- Easy
- Has the most features
- Works everywhere

You can always switch later if needed.

---

Next: Set up your chosen provider with our [Configuration Guide](configuration.md)!