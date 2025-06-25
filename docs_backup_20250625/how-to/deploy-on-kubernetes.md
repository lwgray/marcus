# How to Deploy PM Agent on Kubernetes

> **Goal**: Deploy PM Agent on Kubernetes for scalable, production-grade environments  
> **Time**: 30-45 minutes  
> **When to use**: Production deployments, auto-scaling needs, or multi-region setups

## Prerequisites

Before starting, ensure you have:
- PM Agent version 1.0 or higher
- Kubernetes cluster (1.20+) with kubectl configured
- Helm 3.0+ installed (optional but recommended)
- Docker registry access for images
- Admin access to create resources

## Quick Answer

Deploy PM Agent on Kubernetes:
```bash
# Using kubectl
kubectl create namespace pm-agent
kubectl apply -f https://raw.githubusercontent.com/your-org/pm-agent/main/k8s/deployment.yaml

# Or using Helm
helm repo add pm-agent https://charts.pm-agent.io
helm install pm-agent pm-agent/pm-agent -n pm-agent --create-namespace
```

## Detailed Steps

### 1. Prepare Container Image

Build and push PM Agent Docker image:

```bash
# Build image with proper tag
docker build -t your-registry/pm-agent:v1.0.0 .

# Push to registry
docker push your-registry/pm-agent:v1.0.0

# Or use pre-built image
docker pull ghcr.io/your-org/pm-agent:latest
docker tag ghcr.io/your-org/pm-agent:latest your-registry/pm-agent:latest
docker push your-registry/pm-agent:latest
```

### 2. Create Kubernetes Namespace

Set up a dedicated namespace:

```bash
# Create namespace
kubectl create namespace pm-agent

# Set as default for this session
kubectl config set-context --current --namespace=pm-agent

# Add labels for organization
kubectl label namespace pm-agent app=pm-agent environment=production
```

### 3. Configure Secrets

Create secrets for sensitive data:

```bash
# Create secret for API keys
kubectl create secret generic pm-agent-secrets \
  --from-literal=ANTHROPIC_API_KEY=your-anthropic-key \
  --from-literal=GITHUB_TOKEN=your-github-token \
  --from-literal=LINEAR_API_KEY=your-linear-key

# Create secret from .env file
kubectl create secret generic pm-agent-env --from-env-file=.env

# Verify secrets
kubectl get secrets
kubectl describe secret pm-agent-secrets
```

### 4. Deploy Core Components

Create deployment manifest:

```yaml
# pm-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pm-agent
  namespace: pm-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pm-agent
  template:
    metadata:
      labels:
        app: pm-agent
    spec:
      containers:
      - name: pm-agent
        image: your-registry/pm-agent:v1.0.0
        ports:
        - containerPort: 3100
          name: api
        - containerPort: 8080
          name: metrics
        env:
        - name: KANBAN_PROVIDER
          value: "github"
        - name: PM_AGENT_PORT
          value: "3100"
        envFrom:
        - secretRef:
            name: pm-agent-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3100
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3100
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: config
        configMap:
          name: pm-agent-config
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: pm-agent
  namespace: pm-agent
spec:
  selector:
    app: pm-agent
  ports:
  - name: api
    port: 3100
    targetPort: 3100
  - name: metrics
    port: 8080
    targetPort: 8080
  type: ClusterIP
```

Deploy the application:
```bash
kubectl apply -f pm-agent-deployment.yaml
```

### 5. Configure Ingress

Set up external access:

```yaml
# pm-agent-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pm-agent
  namespace: pm-agent
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - pm-agent.yourdomain.com
    secretName: pm-agent-tls
  rules:
  - host: pm-agent.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pm-agent
            port:
              number: 3100
```

Apply ingress:
```bash
kubectl apply -f pm-agent-ingress.yaml
```

### 6. Set Up Auto-scaling

Configure horizontal pod autoscaling:

```yaml
# pm-agent-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pm-agent
  namespace: pm-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pm-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

Apply autoscaling:
```bash
kubectl apply -f pm-agent-hpa.yaml
```

## Verification

Verify your deployment:
```bash
# Check deployment status
kubectl get deployments
kubectl rollout status deployment/pm-agent

# Check pods
kubectl get pods -l app=pm-agent
kubectl logs -f deployment/pm-agent

# Test service
kubectl port-forward service/pm-agent 3100:3100
curl http://localhost:3100/health

# Check ingress
kubectl get ingress
curl https://pm-agent.yourdomain.com/health
```

You should see:
```
NAME       READY   UP-TO-DATE   AVAILABLE   AGE
pm-agent   3/3     3            3           5m

NAME                        READY   STATUS    RESTARTS   AGE
pm-agent-7d6b9c5f4b-2kx9p   1/1     Running   0          5m
pm-agent-7d6b9c5f4b-8nv4m   1/1     Running   0          5m
pm-agent-7d6b9c5f4b-qw3rt   1/1     Running   0          5m
```

## Options and Variations

### Option 1: Helm Chart Deployment
Use Helm for easier management:
```bash
# Create values.yaml
cat > values.yaml << EOF
replicaCount: 3
image:
  repository: your-registry/pm-agent
  tag: v1.0.0
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 3100

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: pm-agent.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

env:
  KANBAN_PROVIDER: github

secrets:
  create: true
  data:
    ANTHROPIC_API_KEY: your-key
    GITHUB_TOKEN: your-token
EOF

# Install with Helm
helm install pm-agent ./helm/pm-agent -f values.yaml
```

### Option 2: StatefulSet for Persistence
Use StatefulSet for persistent storage:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pm-agent
spec:
  serviceName: pm-agent
  replicas: 3
  selector:
    matchLabels:
      app: pm-agent
  template:
    metadata:
      labels:
        app: pm-agent
    spec:
      containers:
      - name: pm-agent
        image: your-registry/pm-agent:v1.0.0
        volumeMounts:
        - name: data
          mountPath: /app/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

### Option 3: Multi-Region Deployment
Deploy across regions for high availability:
```bash
# Deploy to multiple clusters
for region in us-east-1 eu-west-1 ap-southeast-1; do
  kubectl config use-context k8s-$region
  kubectl apply -f pm-agent-deployment.yaml
done

# Set up global load balancer
kubectl apply -f global-service.yaml
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "ImagePullBackOff" | Check registry credentials: `kubectl create secret docker-registry` |
| "CrashLoopBackOff" | Check logs: `kubectl logs pod-name --previous` |
| "Pending pods" | Check resources: `kubectl describe pod pod-name` |
| "Service unavailable" | Verify endpoints: `kubectl get endpoints` |
| "Ingress not working" | Check ingress controller: `kubectl get pods -n ingress-nginx` |
| "HPA not scaling" | Install metrics server: `kubectl apply -f metrics-server.yaml` |
| "Secret not found" | List secrets: `kubectl get secrets` |
| "Permission denied" | Check RBAC: `kubectl auth can-i --list` |

## Advanced Configuration

### Resource Quotas
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: pm-agent-quota
  namespace: pm-agent
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
```

### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: pm-agent-network-policy
spec:
  podSelector:
    matchLabels:
      app: pm-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3100
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # HTTPS for external APIs
```

### Pod Disruption Budget
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: pm-agent-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: pm-agent
```

## Monitoring and Observability

### Prometheus Monitoring
```yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: pm-agent
spec:
  selector:
    matchLabels:
      app: pm-agent
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### Logging with Fluentd
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/pm-agent/*.log
      tag pm-agent.*
      <parse>
        @type json
      </parse>
    </source>
    <match pm-agent.**>
      @type elasticsearch
      host elasticsearch.logging.svc.cluster.local
      port 9200
      index_name pm-agent
    </match>
```

### Distributed Tracing
```yaml
env:
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: "http://jaeger-collector.tracing.svc.cluster.local:14268"
- name: OTEL_SERVICE_NAME
  value: "pm-agent"
- name: OTEL_TRACES_EXPORTER
  value: "otlp"
```

## Backup and Disaster Recovery

### Velero Backup Configuration
```bash
# Install Velero
velero install --provider aws --bucket pm-agent-backups

# Create backup schedule
velero create schedule pm-agent-daily \
  --schedule="0 2 * * *" \
  --include-namespaces=pm-agent

# Restore from backup
velero restore create --from-backup pm-agent-daily-20240115020000
```

## Related Guides

- [How to Deploy with Docker](/how-to/deploy-with-docker)
- [How to Configure Kubernetes Security](/how-to/k8s-security)
- [How to Monitor PM Agent](/how-to/monitor-pm-agent)
- [Kubernetes Best Practices](/reference/k8s-best-practices)

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [PM Agent Helm Chart](/reference/helm-chart)
- [Kubernetes Patterns](https://k8spatterns.io/)