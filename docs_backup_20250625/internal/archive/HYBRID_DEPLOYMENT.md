# 🔄 PM Agent Hybrid Deployment Guide

## The Problem
Planka has licensing restrictions that may prevent commercial use. However, PM Agent supports multiple kanban providers!

## The Solution: Hybrid Approach

### Option 1: GitHub Issues (Recommended for Most Users)
**Free, no licensing issues, includes code awareness!**

```bash
# 1. Set environment variables
export KANBAN_PROVIDER=github
export GITHUB_TOKEN=your_token
export GITHUB_OWNER=your_username
export GITHUB_REPO=your_repo

# 2. Run with Docker
docker-compose up pm-agent

# That's it! No Planka needed.
```

### Option 2: Linear (For Teams)
**Professional task management, great API**

```bash
# 1. Set environment variables
export KANBAN_PROVIDER=linear
export LINEAR_API_KEY=your_api_key
export LINEAR_TEAM_ID=your_team_id

# 2. Run with Docker
docker-compose up pm-agent
```

### Option 3: Local Planka + Remote PM Agent
**Keep Planka local, expose only PM Agent**

```yaml
# docker-compose.hybrid.yml
version: '3.8'

services:
  # PM Agent with SSE (Public)
  pm-agent:
    build: .
    ports:
      - "8000:8000"  # Only PM Agent is exposed
    environment:
      - KANBAN_PROVIDER=planka
      - PLANKA_URL=http://planka:1337  # Internal connection
    networks:
      - internal

  # Planka (Private - no ports exposed)
  planka:
    image: planka/planka:latest
    # NO PORTS - only accessible by PM Agent
    networks:
      - internal

networks:
  internal:
    driver: bridge
```

## 🚀 Quick Deployment Scripts

### deploy-github.sh
```bash
#!/bin/bash
# Deploy PM Agent with GitHub Issues

cat > .env << EOF
KANBAN_PROVIDER=github
GITHUB_TOKEN=${GITHUB_TOKEN}
GITHUB_OWNER=${GITHUB_OWNER}
GITHUB_REPO=${GITHUB_REPO}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
EOF

docker-compose up -d pm-agent
echo "✅ PM Agent running with GitHub Issues!"
```

### deploy-linear.sh
```bash
#!/bin/bash
# Deploy PM Agent with Linear

cat > .env << EOF
KANBAN_PROVIDER=linear
LINEAR_API_KEY=${LINEAR_API_KEY}
LINEAR_TEAM_ID=${LINEAR_TEAM_ID}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
EOF

docker-compose up -d pm-agent
echo "✅ PM Agent running with Linear!"
```

## 📊 Provider Comparison

| Feature | GitHub Issues | Linear | Planka |
|---------|--------------|--------|---------|
| **License** | ✅ Free | ✅ Commercial OK | ⚠️ AGPL |
| **Remote Access** | ✅ Built-in | ✅ Built-in | ❌ Self-host |
| **Code Awareness** | ✅ Yes | ❌ No | ❌ No |
| **API Quality** | ✅ Excellent | ✅ Excellent | 🔧 Via MCP |
| **Setup Time** | 2 min | 3 min | 10 min |

## 🎯 Recommendations

### For Open Source Projects
Use **GitHub Issues** - it's free, has code awareness, and integrates perfectly.

### For Commercial Teams
Use **Linear** - professional features, great API, no licensing concerns.

### For Private/Experimental Use
Use **Planka** locally - keep it internal, never expose it publicly.

## 🔐 Security Best Practices

1. **Never expose Planka directly** if using it
2. **Use environment variables** for sensitive data
3. **Implement authentication** for remote access
4. **Use HTTPS** in production

## 💡 Advanced: Multi-Provider Setup

You can even run multiple PM Agents for different projects:

```yaml
# docker-compose.multi.yml
services:
  pm-agent-github:
    build: .
    container_name: pm-agent-oss
    environment:
      - KANBAN_PROVIDER=github
    ports:
      - "8001:8000"

  pm-agent-linear:
    build: .
    container_name: pm-agent-commercial
    environment:
      - KANBAN_PROVIDER=linear
    ports:
      - "8002:8000"
```

This way you can use GitHub for open source and Linear for commercial work!