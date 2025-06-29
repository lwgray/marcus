# ⚙️ Configuration Guide

This guide explains all the settings you can change in Marcus.

## 📄 The .env File

All settings live in a file called `.env`. It's like a settings menu for Marcus!

### Creating .env

When you run `./start.sh`, it creates this file automatically. You can also create it yourself:

```bash
cp .env.example .env  # If example exists
# OR
nano .env  # Create from scratch
```

## 🔧 Settings Explained

### Choosing Your Task Board

```bash
KANBAN_PROVIDER=github  # or 'linear' or 'planka'
```

- `github` - Use GitHub Issues (recommended!)
- `linear` - Use Linear (for companies)
- `planka` - Use Planka (local only!)

### GitHub Settings

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo-name
```

**Getting a GitHub Token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name it "Marcus"
4. Check these boxes:
   - ✅ repo (all)
   - ✅ project
5. Click "Generate token"
6. Copy immediately (you can't see it again!)

### Linear Settings

```bash
LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-id
```

**Getting Linear Credentials:**
1. Go to https://linear.app/settings/api
2. Create a personal API key
3. Find your team ID in the URL when viewing your team

### Planka Settings (Local Only!)

```bash
PLANKA_PROJECT_NAME=my-project
PLANKA_SECRET_KEY=some-random-string
```

⚠️ Remember: Planka is for local use only!

### AI Settings

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx  # Future use
```

**Getting Anthropic API Key:**
1. Go to https://console.anthropic.com
2. Create an account
3. Go to API keys section
4. Create new key
5. Add billing method (required)

### Remote Access Settings

```bash
MCP_AUTH_TOKENS=token1,token2,token3
PORT=8000
HOST=0.0.0.0
```

Only needed if hosting online with `./start.sh remote`

## 📝 Example Configurations

### Basic GitHub Setup

```bash
# Simple GitHub setup
KANBAN_PROVIDER=github
GITHUB_TOKEN=ghp_abc123def456
GITHUB_OWNER=johndoe
GITHUB_REPO=my-awesome-project
ANTHROPIC_API_KEY=sk-ant-xyz789
```

### Linear for Teams

```bash
# Professional Linear setup
KANBAN_PROVIDER=linear
LINEAR_API_KEY=lin_api_abc123
LINEAR_TEAM_ID=TEAM-123
ANTHROPIC_API_KEY=sk-ant-xyz789
```

### Local Planka Development

```bash
# Local only - don't use online!
KANBAN_PROVIDER=planka
PLANKA_PROJECT_NAME=personal-project
ANTHROPIC_API_KEY=sk-ant-xyz789
```

## 🎯 Advanced Settings

### Logging Level

```bash
LOG_LEVEL=INFO  # or DEBUG, WARNING, ERROR
```

- `DEBUG` - Everything (very verbose!)
- `INFO` - Normal operation (default)
- `WARNING` - Only problems
- `ERROR` - Only serious issues

### Worker Settings

Edit `prompts/system_prompts.md` to change how workers behave!

### Docker Settings

Edit `docker-compose.yml` for:
- Memory limits
- CPU limits
- Volume mounts
- Network settings

## 🔒 Security Tips

1. **Never commit .env to Git!** (it's in .gitignore)
2. **Keep backups** of your .env file
3. **Use strong tokens** for remote access
4. **Rotate API keys** regularly
5. **Set file permissions**:
   ```bash
   chmod 600 .env  # Only you can read/write
   ```

## 🔄 Changing Settings

After changing .env:

```bash
docker-compose restart
```

Or for complete reload:

```bash
docker-compose down
./start.sh
```

## 🧪 Testing Your Configuration

### Test GitHub Connection
```bash
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
     https://api.github.com/user
```

### Test Anthropic Key
```bash
curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: YOUR_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "content-type: application/json" \
     -X POST \
     -d '{"model":"claude-3-haiku-20240307","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'
```

## 💡 Configuration Best Practices

1. **Start simple** - Just GitHub + Anthropic
2. **One provider at a time** - Don't mix boards
3. **Test locally first** - Use `./start.sh demo`
4. **Document your setup** - Note what works
5. **Regular backups** - Save your working .env

---

Need help? Check [Troubleshooting](reference/troubleshooting) or [FAQ](reference/faq)!