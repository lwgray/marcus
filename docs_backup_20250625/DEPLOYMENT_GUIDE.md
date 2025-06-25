# 🚀 PM Agent Deployment Guide

## Quick Decision Tree

```
Are you hosting PM Agent publicly/remotely?
├─ YES → Use GitHub or Linear (NOT Planka)
│   └─ Run: ./start.sh remote
└─ NO (local only)
    └─ Any provider is fine
        ├─ GitHub → ./start.sh
        ├─ Linear → ./start.sh  
        └─ Planka → ./start.sh local-planka
```

## Provider Comparison

| Provider | License OK? | Remote OK? | Setup Time | Best For |
|----------|------------|------------|------------|----------|
| **GitHub** | ✅ Yes | ✅ Yes | 2 min | Most users |
| **Linear** | ✅ Yes | ✅ Yes | 3 min | Pro teams |
| **Planka** | ⚠️ AGPL | ❌ No | 5 min | Local only |

## Deployment Scenarios

### 1. 🌐 Remote/Cloud Deployment (Recommended: GitHub)

```bash
# Setup for remote deployment
./start.sh remote

# Edit .env - use GitHub or Linear ONLY
nano .env

# Deploy to your cloud provider
docker-compose -f docker-compose.remote.yml up -d
```

**Available Providers**: GitHub ✅, Linear ✅, ~~Planka~~ ❌

### 2. 💻 Local Development (All Providers Available)

```bash
# Option A: GitHub (recommended)
KANBAN_PROVIDER=github ./start.sh

# Option B: Linear
KANBAN_PROVIDER=linear ./start.sh

# Option C: Planka (local only!)
KANBAN_PROVIDER=planka ./start.sh local-planka
```

### 3. 🏢 Internal Company Network

If hosting on internal network (not public internet):
- All providers technically OK
- Still recommend GitHub/Linear for simplicity
- If using Planka, ensure it's not accessible externally

## Step-by-Step Setup

### For GitHub (Recommended)

1. Create a GitHub repo (private or public)
2. Get a GitHub token: https://github.com/settings/tokens
3. Configure:
   ```bash
   export KANBAN_PROVIDER=github
   export GITHUB_TOKEN=your_token
   export GITHUB_OWNER=your_username
   export GITHUB_REPO=your_repo
   ```
4. Run: `./start.sh` or `./start.sh remote`

### For Linear

1. Get Linear API key: https://linear.app/settings/api
2. Find your team ID in Linear settings
3. Configure:
   ```bash
   export KANBAN_PROVIDER=linear
   export LINEAR_API_KEY=your_key
   export LINEAR_TEAM_ID=your_team_id
   ```
4. Run: `./start.sh` or `./start.sh remote`

### For Planka (LOCAL ONLY)

1. Ensure you're only running locally
2. Configure:
   ```bash
   export KANBAN_PROVIDER=planka
   ```
3. Run: `./start.sh local-planka`
4. Access Planka at http://localhost:1337

## Security Best Practices

### For Remote Deployments
- Use environment variables for secrets
- Enable authentication (MCP_AUTH_TOKENS)
- Use HTTPS with proper certificates
- Regular security updates

### For Local Deployments
- Keep ports bound to localhost
- Use strong passwords even locally
- Don't expose Docker daemon

## Common Issues

### "Can I use Planka for my SaaS?"
**No.** Planka's AGPL license would require you to open-source your entire application.

### "Can I use Planka on my company's internal network?"
**Technically yes**, but we recommend GitHub/Linear to avoid any licensing complications.

### "Which provider has the best features?"
- **GitHub**: Best integration, code awareness, free
- **Linear**: Best UI, professional features
- **Planka**: Simple, self-contained (but AGPL)

## Migration Guide

### Moving from Planka to GitHub
1. Export tasks from Planka (manual process)
2. Create GitHub issues for each task
3. Update .env: `KANBAN_PROVIDER=github`
4. Restart PM Agent

### Moving from Planka to Linear
1. Linear has import tools for various formats
2. Update .env: `KANBAN_PROVIDER=linear`
3. Restart PM Agent

## Final Recommendations

1. **For Open Source Projects**: Use GitHub Issues
2. **For Commercial Products**: Use GitHub or Linear
3. **For Personal Experiments**: Any provider (including Planka locally)
4. **For Public SaaS**: GitHub or Linear ONLY

Remember: When in doubt, choose GitHub - it's free, powerful, and has zero licensing concerns!