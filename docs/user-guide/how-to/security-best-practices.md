# How to Secure Marcus Deployment

> **Goal**: Implement security best practices for Marcus in production  
> **Time**: 30-60 minutes depending on requirements  
> **When to use**: Any production deployment or when handling sensitive data

## Prerequisites

Before starting, ensure you have:
- Marcus deployed (Docker, Python, or Kubernetes)
- Admin access to your deployment environment
- SSL/TLS certificates (or ability to generate them)
- Understanding of your security requirements

## Quick Answer

Essential security measures:
```bash
# 1. Use environment variables for secrets
export ANTHROPIC_API_KEY=$(vault read -field=key secret/pm-agent/anthropic)

# 2. Enable HTTPS
./start.sh --enable-ssl --cert-file cert.pem --key-file key.pem

# 3. Set up authentication
export PM_AGENT_AUTH_ENABLED=true
export PM_AGENT_AUTH_TOKENS=$(openssl rand -hex 32)

# 4. Restrict network access
iptables -A INPUT -p tcp --dport 3100 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 3100 -j DROP
```

## Detailed Steps

### 1. Secure Secret Management

Implement proper secret handling:

#### Using Environment Variables
```bash
# Never commit .env files
echo ".env" >> .gitignore
echo ".env.*" >> .gitignore

# Use a secure secret manager
# HashiCorp Vault example:
vault kv put secret/pm-agent \
  anthropic_api_key="$ANTHROPIC_API_KEY" \
  github_token="$GITHUB_TOKEN"

# Load secrets at runtime
export ANTHROPIC_API_KEY=$(vault kv get -field=anthropic_api_key secret/pm-agent)
export GITHUB_TOKEN=$(vault kv get -field=github_token secret/pm-agent)
```

#### Using Docker Secrets
```yaml
# docker-compose.yml with secrets
version: '3.8'
services:
  pm-agent:
    image: pm-agent:latest
    secrets:
      - anthropic_key
      - github_token
    environment:
      ANTHROPIC_API_KEY_FILE: /run/secrets/anthropic_key
      GITHUB_TOKEN_FILE: /run/secrets/github_token

secrets:
  anthropic_key:
    external: true
  github_token:
    external: true
```

#### Using Kubernetes Secrets
```bash
# Create sealed secret
echo -n 'your-api-key' | kubectl create secret generic pm-agent-secrets \
  --dry-run=client --from-file=anthropic-key=/dev/stdin -o yaml | \
  kubeseal -o yaml > sealed-secrets.yaml

# Apply sealed secret
kubectl apply -f sealed-secrets.yaml
```

### 2. Enable HTTPS/TLS

Configure SSL/TLS encryption:

#### Generate Certificates
```bash
# Self-signed for testing
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
  -days 365 -nodes -subj "/CN=pm-agent.local"

# Let's Encrypt for production
certbot certonly --standalone -d pm-agent.yourdomain.com
```

#### Configure Marcus
```python
# config/security.py
SSL_CONFIG = {
    'enabled': True,
    'cert_file': '/etc/pm-agent/certs/cert.pem',
    'key_file': '/etc/pm-agent/certs/key.pem',
    'ca_file': '/etc/pm-agent/certs/ca.pem',
    'verify_mode': 'CERT_REQUIRED',
    'ciphers': 'TLSv1.2:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4'
}

# Force HTTPS redirect
FORCE_HTTPS = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

#### Nginx Reverse Proxy
```nginx
# /etc/nginx/sites-available/pm-agent
server {
    listen 443 ssl http2;
    server_name pm-agent.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/pm-agent.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pm-agent.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://localhost:3100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Implement Authentication

Set up access control:

#### API Key Authentication
```python
# config/auth.py
import secrets
import hashlib

# Generate API keys
def generate_api_key():
    return secrets.token_urlsafe(32)

# Store hashed keys
API_KEYS = {
    hashlib.sha256("your-api-key".encode()).hexdigest(): {
        "name": "worker-agent-1",
        "permissions": ["read", "write"]
    }
}

# Middleware for verification
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or not verify_api_key(api_key):
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

#### OAuth2 Integration
```python
# config/oauth.py
from authlib.integrations.flask_client import OAuth

oauth = OAuth()
oauth.register(
    name='github',
    client_id='your-github-oauth-app-id',
    client_secret='your-github-oauth-secret',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)
```

### 4. Network Security

Restrict network access:

#### Firewall Rules
```bash
# UFW (Ubuntu)
ufw default deny incoming
ufw default allow outgoing
ufw allow from 10.0.0.0/8 to any port 3100
ufw allow 22/tcp  # SSH
ufw allow 443/tcp # HTTPS
ufw enable

# iptables
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 3100 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 3100 -j DROP
iptables-save > /etc/iptables/rules.v4
```

#### Network Segmentation
```yaml
# docker-compose.yml with networks
version: '3.8'

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

services:
  pm-agent:
    networks:
      - frontend
      - backend
  
  database:
    networks:
      - backend  # Only accessible from backend
```

### 5. Data Protection

Implement data security measures:

#### Encryption at Rest
```python
# config/encryption.py
from cryptography.fernet import Fernet

# Generate encryption key
encryption_key = Fernet.generate_key()

# Encrypt sensitive data
def encrypt_data(data: str) -> bytes:
    f = Fernet(encryption_key)
    return f.encrypt(data.encode())

# Decrypt data
def decrypt_data(encrypted_data: bytes) -> str:
    f = Fernet(encryption_key)
    return f.decrypt(encrypted_data).decode()
```

#### Database Security
```sql
-- Create restricted user
CREATE USER 'pm_agent_app'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON pm_agent.* TO 'pm_agent_app'@'localhost';

-- Enable SSL for connections
ALTER USER 'pm_agent_app'@'localhost' REQUIRE SSL;
```

### 6. Audit and Monitoring

Set up security monitoring:

#### Audit Logging
```python
# config/audit.py
import logging
from datetime import datetime

audit_logger = logging.getLogger('security_audit')
audit_handler = logging.FileHandler('/var/log/pm-agent/audit.log')
audit_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
audit_logger.addHandler(audit_handler)

def log_security_event(event_type, user, details):
    audit_logger.info(f"{event_type} - User: {user} - Details: {details}")
```

#### Intrusion Detection
```bash
# Install and configure fail2ban
apt-get install fail2ban

# Create jail configuration
cat > /etc/fail2ban/jail.d/pm-agent.conf << EOF
[pm-agent]
enabled = true
port = 3100
filter = pm-agent
logpath = /var/log/pm-agent/access.log
maxretry = 5
bantime = 3600
EOF

# Create filter
cat > /etc/fail2ban/filter.d/pm-agent.conf << EOF
[Definition]
failregex = ^<HOST> .* 401 .*$
            ^<HOST> .* 403 .*$
ignoreregex =
EOF
```

## Verification

Verify security measures:
```bash
# Test SSL/TLS
openssl s_client -connect pm-agent.yourdomain.com:443 -tls1_2

# Check security headers
curl -I https://pm-agent.yourdomain.com

# Scan for vulnerabilities
nmap -sV --script ssl-enum-ciphers -p 443 pm-agent.yourdomain.com

# Test authentication
curl -H "X-API-Key: invalid-key" https://pm-agent.yourdomain.com/api/health
# Should return 401 Unauthorized
```

## Options and Variations

### Option 1: Zero Trust Security
Implement zero trust architecture:
```yaml
# Istio service mesh configuration
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: pm-agent-authz
spec:
  selector:
    matchLabels:
      app: pm-agent
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/worker-agent"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]
```

### Option 2: Hardware Security Module
Use HSM for key management:
```python
# config/hsm.py
import pkcs11

# Initialize HSM
lib = pkcs11.lib('/usr/lib/softhsm/libsofthsm2.so')
token = lib.get_token(token_label='PM_AGENT_HSM')

# Generate key in HSM
with token.open(user_pin='1234') as session:
    key = session.generate_key(
        pkcs11.KeyType.AES,
        256,
        label='pm_agent_master_key'
    )
```

### Option 3: Compliance Mode
Enable compliance features:
```python
# config/compliance.py
COMPLIANCE_MODE = 'HIPAA'  # or 'PCI-DSS', 'SOC2'

COMPLIANCE_SETTINGS = {
    'HIPAA': {
        'audit_logging': True,
        'encryption_required': True,
        'session_timeout': 900,  # 15 minutes
        'password_complexity': 'high',
        'data_retention_days': 2555  # 7 years
    }
}
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "SSL: CERTIFICATE_VERIFY_FAILED" | Check certificate chain and CA bundle |
| "401 Unauthorized" | Verify API key format and permissions |
| "Connection refused" | Check firewall rules and port bindings |
| "Too many redirects" | Ensure proper HTTPS configuration in reverse proxy |
| "Permission denied" | Check file permissions and SELinux contexts |
| "Cipher mismatch" | Update TLS configuration to support modern ciphers |
| "Token expired" | Implement token refresh mechanism |
| "Audit log full" | Set up log rotation with logrotate |

## Security Checklist

Before going to production:

- [ ] All secrets in secure storage (not in code)
- [ ] HTTPS enabled with valid certificates
- [ ] Authentication required for all endpoints
- [ ] Network access restricted by firewall
- [ ] Audit logging enabled
- [ ] Regular security updates scheduled
- [ ] Backup encryption configured
- [ ] Incident response plan documented
- [ ] Security monitoring alerts configured
- [ ] Penetration testing completed

## Compliance Considerations

### GDPR Compliance
```python
# Enable data privacy features
GDPR_COMPLIANCE = {
    'data_minimization': True,
    'right_to_erasure': True,
    'data_portability': True,
    'consent_required': True,
    'breach_notification': True
}
```

### SOC 2 Requirements
- Implement change management
- Document security policies
- Regular security training
- Vendor risk assessments
- Business continuity planning

## Related Guides

- [How to Monitor Marcus](/how-to/monitor-pm-agent)
- [How to Backup Marcus](/how-to/backup-restore)
- [Security Reference](/reference/security)
- [Compliance Guide](/reference/compliance)

## References

- [OWASP Security Practices](https://owasp.org/www-project-web-security-testing-guide/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Security Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [Marcus Security Documentation](/reference/security)