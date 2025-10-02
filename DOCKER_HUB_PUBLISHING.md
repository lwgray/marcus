# Publishing Marcus to Docker Hub

This guide explains how to publish the Marcus Docker image to Docker Hub so users can run it without building from source.

## Prerequisites

1. **Docker Hub Account**
   - Create an account at [hub.docker.com](https://hub.docker.com)
   - Choose a username (e.g., `marcusai`, `marcus-project`, etc.)

2. **Docker CLI Access**
   - Install Docker Desktop or Docker Engine
   - Log in to Docker Hub from the command line

## Publishing Steps

### 1. Create Docker Hub Repository

```bash
# Option A: Via Web Interface
# 1. Go to https://hub.docker.com
# 2. Click "Create Repository"
# 3. Name: marcus
# 4. Visibility: Public
# 5. Description: "AI Agent Coordination Platform - Autonomous multi-agent software development"

# Option B: Via CLI (requires Docker Hub account setup)
# This will be created automatically when you push
```

### 2. Log In to Docker Hub

```bash
docker login
# Enter your Docker Hub username and password
```

### 3. Build and Tag the Image

```bash
# Navigate to Marcus directory
cd /path/to/marcus

# Build the image with proper tags
# IMPORTANT: The '.' at the end specifies the build context (current directory) - don't forget it!
# Replace 'yourusername' with your Docker Hub username
docker build -t yourusername/marcus:latest .

# Optionally, also tag with a version number
docker build -t yourusername/marcus:v1.0.0 .

# Example for username 'lwgray575':
docker build -t lwgray575/marcus:latest .
docker build -t lwgray575/marcus:v1.0.0 .
```

### 4. Push to Docker Hub

```bash
# Push both tags
docker push yourusername/marcus:latest
docker push yourusername/marcus:v1.0.0

# This will upload the image to Docker Hub
# First push may take several minutes (image is ~779MB)
```

### 5. Verify Publication

```bash
# Test pulling your published image
docker pull yourusername/marcus:latest

# Or visit: https://hub.docker.com/r/yourusername/marcus
```

## Updating the README

Once published, update the README.md to use the actual Docker Hub image:

```bash
# Current (build from source):
git clone https://github.com/lwgray/marcus.git
cd marcus
docker build -t marcus .

# After publishing (direct pull):
docker pull yourusername/marcus:latest
docker run -p 4298:4298 \
  -e MARCUS_KANBAN_PROVIDER=github \
  -e MARCUS_KANBAN_GITHUB_TOKEN=ghp_your_token \
  -e MARCUS_KANBAN_GITHUB_OWNER=your_username \
  -e MARCUS_KANBAN_GITHUB_REPO=your_repo \
  -e MARCUS_AI_ANTHROPIC_API_KEY=sk-ant-your_key \
  yourusername/marcus:latest
```

## Automated Publishing with GitHub Actions

For continuous deployment, create `.github/workflows/docker-publish.yml`:

```yaml
name: Publish Docker Image

on:
  release:
    types: [published]
  push:
    branches:
      - main
    tags:
      - 'v*'

jobs:
  push_to_registry:
    name: Push Docker image to Docker Hub
    runs-on: ubuntu-latest
    steps:
      - name: Check out the repo
        uses: actions/checkout@v4

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_HUB_USERNAME }}
          password: ${{ secrets.DOCKER_HUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: yourusername/marcus
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

### Setting Up GitHub Secrets

1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Add two secrets:
   - `DOCKER_HUB_USERNAME`: Your Docker Hub username
   - `DOCKER_HUB_TOKEN`: Generate at [hub.docker.com/settings/security](https://hub.docker.com/settings/security)

## Version Tagging Strategy

Use semantic versioning for tags:

```bash
# Major release (breaking changes)
docker build -t yourusername/marcus:v2.0.0 .
docker build -t yourusername/marcus:2 .
docker build -t yourusername/marcus:latest .

# Minor release (new features)
docker build -t yourusername/marcus:v1.1.0 .
docker build -t yourusername/marcus:1.1 .
docker build -t yourusername/marcus:1 .
docker build -t yourusername/marcus:latest .

# Patch release (bug fixes)
docker build -t yourusername/marcus:v1.0.1 .
docker build -t yourusername/marcus:1.0.1 .
```

## Best Practices

1. **Always tag with version numbers** - Don't rely solely on `latest`
2. **Update latest on stable releases** - Not on every commit
3. **Include release notes** - Document changes in Docker Hub description
4. **Test before publishing** - Run the image locally first
5. **Monitor image size** - Current size is ~779MB, optimize if needed

## Reducing Image Size (Optional)

To reduce the 779MB image size:

```dockerfile
# Use multi-stage builds
FROM python:3.11-slim as builder
# ... build dependencies ...

FROM python:3.11-slim
# Copy only what's needed from builder
COPY --from=builder /app /app
```

## Support

After publishing:
- Update README.md with correct Docker Hub commands
- Add badge: `[![Docker](https://img.shields.io/docker/pulls/yourusername/marcus)](https://hub.docker.com/r/yourusername/marcus)`
- Link to Docker Hub in documentation
