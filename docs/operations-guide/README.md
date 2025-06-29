# Operations Guide

Welcome to the Marcus Operations Guide! This directory contains everything needed to deploy, configure, and operate Marcus in production.

## 📚 Contents

### Core Documentation
- [**Deployment Guide**](deployment.md) - Complete deployment options
- [**Monitoring Guide**](monitoring.md) - Monitoring and observability (if available)

### Setup Guides
The [setup/](setup/) directory contains provider-specific setup instructions:
- Docker setup
- Kubernetes deployment
- Cloud provider guides
- Environment configuration

## 🧭 Navigation Guide

### By Deployment Type

**Local Development**
1. Follow [Deployment Guide](deployment.md) - Local Setup section
2. Use Docker Compose for easy local deployment
3. Check environment configuration in [setup/](setup/)

**Cloud Deployment**
1. Read [Deployment Guide](deployment.md) - Cloud Deployment section
2. Choose your cloud provider
3. Follow specific guides in [setup/](setup/)

**Production Deployment**
1. Review entire [Deployment Guide](deployment.md)
2. Set up monitoring (see [Monitoring Guide](monitoring.md))
3. Configure for high availability

## 🔧 Common Operations Tasks

### Initial Setup
- Environment variables configuration
- Database setup
- API key management
- Provider selection (GitHub, Linear, Planka)

### Maintenance
- Log rotation
- Backup procedures
- Update processes
- Performance tuning

### Troubleshooting
- Check logs in `/logs` directory
- Review common issues in [User Guide](../user-guide/how-to/troubleshoot-common-issues.md)
- Monitor system health

## 📋 Quick Reference

### Environment Variables
```bash
# Kanban Provider
KANBAN_PROVIDER=github  # or linear, planka

# GitHub Setup
GITHUB_TOKEN=your_token
GITHUB_OWNER=your_org
GITHUB_REPO=your_repo

# AI Configuration
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
```

### Docker Commands
```bash
# Start Marcus
docker-compose up -d

# View logs
docker-compose logs -f marcus

# Stop Marcus
docker-compose down
```

## 🔍 Can't Find Something?

- Check the main [Documentation Hub](../README.md)
- Look in [User Guide](../user-guide/) for usage documentation
- See [Developer Guide](../developer-guide/) for technical details

---

[← Back to Documentation Hub](../README.md)