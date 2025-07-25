# Marcus Deployment Security Guide

## Overview

Marcus is an open-source tool where security is managed at the deployment and infrastructure level, not within the application itself. This guide covers best practices for securing Marcus in production environments.

## Key Security Principle

**Anyone who can run Marcus has full admin access.** Role-based access control in Marcus is for organization and preventing accidents, not for security.

## Deployment Security Strategies

### 1. Network Isolation

#### Private Network Deployment
```bash
# Run Marcus only on internal networks
./run_marcus.py --http --host 10.0.0.100 --port 4298
```

#### VPN-Only Access
- Deploy Marcus behind VPN
- Require VPN connection for all clients
- Use network ACLs to restrict access

### 2. Reverse Proxy with Authentication

#### Nginx with Basic Auth
```nginx
server {
    listen 443 ssl;
    server_name marcus.internal.company.com;

    # SSL configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Basic authentication
    auth_basic "Marcus Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location /mcp {
        proxy_pass http://localhost:4298;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### Traefik with OAuth2
```yaml
# docker-compose.yml
services:
  traefik:
    image: traefik:v2.9
    command:
      - "--providers.docker=true"
      - "--entrypoints.websecure.address=:443"
    labels:
      - "traefik.http.middlewares.oauth.forwardauth.address=https://oauth.company.com"
      - "traefik.http.middlewares.oauth.forwardauth.trustForwardHeader=true"

  marcus:
    image: marcus:latest
    labels:
      - "traefik.http.routers.marcus.middlewares=oauth@docker"
      - "traefik.http.routers.marcus.entrypoints=websecure"
```

### 3. Container Security

#### Docker Deployment
```dockerfile
FROM python:3.11-slim
# Run as non-root user
RUN useradd -m -u 1000 marcus
USER marcus

# Copy only necessary files
COPY --chown=marcus:marcus src/ /app/src/
COPY --chown=marcus:marcus config_marcus.json /app/

WORKDIR /app
# Read-only filesystem
RUN chmod -R 555 /app/src
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: marcus
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: marcus
        image: marcus:latest
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
```

### 4. Access Control

#### OS-Level Permissions (Linux)
```bash
# Create marcus user
sudo useradd -r -s /bin/false marcus

# Set ownership
sudo chown -R marcus:marcus /opt/marcus
sudo chmod 750 /opt/marcus
sudo chmod 640 /opt/marcus/config_marcus.json

# Only marcus user can run
sudo -u marcus /opt/marcus/run_marcus.py
```

#### Systemd Service
```ini
[Unit]
Description=Marcus MCP Server
After=network.target

[Service]
Type=simple
User=marcus
Group=marcus
WorkingDirectory=/opt/marcus
ExecStart=/usr/bin/python3 /opt/marcus/run_marcus.py --http
Restart=on-failure
# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/marcus/data

[Install]
WantedBy=multi-user.target
```

### 5. Secrets Management

#### Environment Variables
```bash
# Don't store secrets in config_marcus.json
export ANTHROPIC_API_KEY="sk-ant-..."  # pragma: allowlist secret
export PLANKA_PASSWORD="..."
export GITHUB_TOKEN="..."
```

#### HashiCorp Vault Integration
```python
# Custom config loader
import hvac

client = hvac.Client(url='https://vault.company.com')
secrets = client.secrets.kv.v2.read_secret_version(path='marcus/prod')

config['ai']['anthropic_api_key'] = secrets['data']['data']['anthropic_api_key']
config['planka']['password'] = secrets['data']['data']['planka_password']
```

### 6. Audit Logging

#### Centralized Logging
```python
# Send logs to centralized system
import logging
from pythonjsonlogger import jsonlogger

# JSON formatter for log aggregation
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

#### Log Shipping
```yaml
# Filebeat configuration
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /opt/marcus/logs/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch.company.com:9200"]
  index: "marcus-%{+yyyy.MM.dd}"
```

### 7. Monitoring & Alerting

#### Health Checks
```python
# Health endpoint for monitoring
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": __version__
    }
```

#### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('marcus_requests_total', 'Total requests', ['method', 'client_type'])
request_duration = Histogram('marcus_request_duration_seconds', 'Request duration')

# Expose metrics
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Security Checklist

- [ ] Marcus runs on private network only
- [ ] Access requires VPN or internal network
- [ ] Reverse proxy handles authentication
- [ ] Running as non-root user
- [ ] File permissions properly set
- [ ] Secrets in environment variables, not config
- [ ] Audit logging enabled
- [ ] Health monitoring in place
- [ ] Regular security updates applied
- [ ] Backup strategy implemented

## Example Production Architecture

```
Internet
    |
[WAF/CDN]
    |
[Load Balancer]
    |
[Auth Proxy (nginx/traefik)]
    |            |
[Marcus-1]  [Marcus-2]  (Multiple instances)
    |            |
[Shared State Store]
    |
[Audit Log Aggregator]
```

## Summary

Remember: Marcus's role-based access control helps organize tool usage and prevent accidents. Real security comes from:
1. Controlling who can access the infrastructure
2. Network isolation and firewalls
3. Authentication at the proxy level
4. Proper secrets management
5. Comprehensive audit logging

Treat Marcus like any internal tool - secure the perimeter, not the application.
