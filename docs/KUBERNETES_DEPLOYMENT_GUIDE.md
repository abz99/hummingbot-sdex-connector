# Stellar Hummingbot Connector v3 - Kubernetes Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Stellar Hummingbot Connector v3 to Kubernetes using both Kustomize and Helm approaches. The deployment includes production-grade observability, security, and scalability features.

## 🏗️ Architecture Overview

### Components
- **Stellar Connector**: Main trading application with 3-15 replicas (auto-scaling)
- **Monitoring Stack**: Prometheus, Grafana, Alertmanager
- **Storage**: Redis (cache), PostgreSQL (optional)
- **Networking**: Ingress with TLS termination, Network policies
- **Security**: RBAC, Pod Security Standards, Secret management

### Deployment Methods
1. **Kustomize**: GitOps-friendly, environment overlays
2. **Helm**: Package management, templating, dependency management

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (v1.21+)
- kubectl configured
- Either kustomize (v4.0+) or Helm (v3.8+)
- Docker registry access

### Option 1: Kustomize Deployment

```bash
# Clone the repository
git clone https://github.com/stellar/hummingbot-connector-v3
cd hummingbot-connector-v3

# Deploy to production
./scripts/deploy_to_kubernetes.sh --environment production

# Or deploy with custom settings
./scripts/deploy_to_kubernetes.sh \
  --environment production \
  --image-tag v3.0.1 \
  --registry your-registry.com \
  --namespace stellar-prod
```

### Option 2: Helm Deployment

```bash
# Add Helm repository (when available)
helm repo add stellar https://charts.stellar.org
helm repo update

# Install with default values
helm install stellar-connector stellar/stellar-hummingbot-connector \
  --namespace stellar-production \
  --create-namespace

# Install with custom values
helm install stellar-connector stellar/stellar-hummingbot-connector \
  --namespace stellar-production \
  --create-namespace \
  --values values-production.yaml
```

## 📁 Directory Structure

```
k8s/
├── base/                          # Base Kubernetes manifests
│   ├── deployment.yaml           # Main application deployment
│   ├── service.yaml              # Service definition
│   ├── configmap.yaml            # Configuration
│   ├── secret.yaml               # Secrets template
│   ├── hpa.yaml                  # Auto-scaling configuration
│   ├── monitoring.yaml           # Monitoring stack
│   └── rbac.yaml                 # RBAC policies
├── overlays/
│   ├── development/              # Development environment
│   ├── staging/                  # Staging environment
│   └── production/               # Production environment
│       ├── kustomization.yaml   # Kustomize configuration
│       ├── deployment-patch.yaml # Production overrides
│       ├── ingress.yaml         # Ingress configuration
│       └── production.env       # Environment variables
└── helm/
    └── stellar-hummingbot-connector/
        ├── Chart.yaml            # Helm chart metadata
        ├── values.yaml           # Default values
        ├── templates/            # Kubernetes templates
        └── charts/               # Chart dependencies
```

## 🔧 Configuration

### Environment Variables

#### Core Application
```yaml
ENVIRONMENT: production
LOG_LEVEL: WARN
STELLAR_NETWORK: MAINNET
TRADING_ENABLED: "true"
ARBITRAGE_ENABLED: "true"
```

#### Performance Settings
```yaml
MAX_CONCURRENT_OPERATIONS: 200
REQUEST_TIMEOUT: 45
CIRCUIT_BREAKER_THRESHOLD: 10
DATABASE_POOL_SIZE: 50
REDIS_POOL_SIZE: 20
```

#### Security Settings
```yaml
ENCRYPTION_ENABLED: "true"
AUDIT_LOGGING_ENABLED: "true"
SECURITY_MONITORING_ENABLED: "true"
```

### Secrets Management

#### Required Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: stellar-secrets
stringData:
  stellar-secret-key: "YOUR_STELLAR_SECRET_KEY"
  database-url: "postgresql://user:pass@host:5432/db"
  redis-url: "redis://:password@host:6379/0"
```

#### Optional Secrets
- HSM integration keys
- External API keys (CoinGecko, etc.)
- Notification webhooks (Slack, Discord)
- SSL/TLS certificates

### Resource Requirements

#### Production Recommendations
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1500m"
```

#### Node Requirements
- **Minimum**: 2 nodes, 4 vCPU, 8GB RAM each
- **Recommended**: 3+ nodes, 8 vCPU, 16GB RAM each
- **Storage**: SSD-backed persistent volumes

## 📊 Monitoring and Observability

### Metrics Collection
- **Prometheus**: Metrics scraping and storage
- **Grafana**: Visualization dashboards
- **Alertmanager**: Alert routing and notifications

### Key Metrics
- Trading volume and revenue
- Order execution latency
- System resource utilization
- Error rates and availability
- Business KPIs

### Dashboards
1. **Executive Dashboard**: Business metrics and KPIs
2. **Technical Dashboard**: System performance and health
3. **Security Dashboard**: Security events and compliance

### Alerts
- **Critical**: System down, high error rates
- **Warning**: Performance degradation, resource limits
- **Info**: Business milestones, deployment events

## 🔐 Security Configuration

### Pod Security
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000
containerSecurityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false
  capabilities:
    drop: ["ALL"]
```

### Network Security
- **Network Policies**: Restrict pod-to-pod communication
- **Ingress Security**: TLS termination, rate limiting
- **RBAC**: Least-privilege service accounts

### Secret Security
- **Encrypted at rest**: etcd encryption
- **Secret rotation**: Automated key rotation
- **HSM integration**: Hardware security modules

## ⚡ Scaling and Performance

### Horizontal Pod Autoscaler (HPA)
```yaml
minReplicas: 3
maxReplicas: 15
targetCPUUtilizationPercentage: 60
targetMemoryUtilizationPercentage: 70
```

### Custom Metrics Scaling
- Concurrent operations count
- Request rate per second
- Trading volume metrics
- Queue length metrics

### Vertical Pod Autoscaler (VPA)
- Automatic resource recommendation
- Right-sizing containers
- Cost optimization

## 🌍 Multi-Environment Deployment

### Environment Isolation
- **Development**: Single replica, relaxed security
- **Staging**: Production-like, synthetic data
- **Production**: Multi-replica, full security

### GitOps Workflow
1. **Code changes**: Feature branch development
2. **Testing**: Automated testing pipeline
3. **Staging**: Deploy to staging environment
4. **Production**: Promote to production after approval

### Environment-Specific Configurations
```bash
# Development
./scripts/deploy_to_kubernetes.sh --environment development

# Staging  
./scripts/deploy_to_kubernetes.sh --environment staging

# Production
./scripts/deploy_to_kubernetes.sh --environment production
```

## 🔄 Deployment Operations

### Rolling Updates
```bash
# Update image version
kubectl set image deployment/stellar-connector \
  stellar-connector=stellar/hummingbot-connector:v3.0.1

# Check rollout status
kubectl rollout status deployment/stellar-connector
```

### Rollback
```bash
# View rollout history
kubectl rollout history deployment/stellar-connector

# Rollback to previous version
kubectl rollout undo deployment/stellar-connector

# Rollback to specific revision
kubectl rollout undo deployment/stellar-connector --to-revision=2
```

### Scaling
```bash
# Manual scaling
kubectl scale deployment/stellar-connector --replicas=5

# Check HPA status
kubectl get hpa

# View VPA recommendations
kubectl describe vpa stellar-connector-vpa
```

## 🩺 Health Checks and Monitoring

### Health Check Endpoints
- **Liveness**: `/health/live` - Is the application running?
- **Readiness**: `/health/ready` - Is the application ready to serve traffic?
- **Startup**: `/health/startup` - Has the application finished starting?

### Monitoring Access
```bash
# Port-forward to Grafana
kubectl port-forward -n stellar-monitoring service/grafana-service 3000:3000

# Port-forward to Prometheus
kubectl port-forward -n stellar-monitoring service/prometheus-service 9090:9090

# View application metrics
curl http://localhost:8000/metrics
```

## 🚨 Troubleshooting

### Common Issues

#### Pod Startup Failures
```bash
# Check pod status
kubectl get pods -l app=stellar-hummingbot-connector

# Describe problematic pod
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name> --previous
```

#### Resource Constraints
```bash
# Check resource usage
kubectl top pods
kubectl top nodes

# Check HPA status
kubectl describe hpa stellar-connector-hpa

# Check resource quotas
kubectl describe resourcequota
```

#### Network Issues
```bash
# Check service endpoints
kubectl get endpoints

# Test service connectivity
kubectl run debug --image=busybox -it --rm -- /bin/sh
```

#### Configuration Issues
```bash
# Check ConfigMap
kubectl describe configmap stellar-config

# Check Secrets
kubectl describe secret stellar-secrets

# Verify environment variables
kubectl exec <pod-name> -- env | grep STELLAR
```

### Debugging Commands
```bash
# Interactive debugging
kubectl exec -it <pod-name> -- /bin/bash

# Check application logs
kubectl logs -f deployment/stellar-connector

# Monitor events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check resource consumption
kubectl describe node <node-name>
```

## 📚 Best Practices

### Deployment
1. **Use namespace isolation** for environments
2. **Implement proper RBAC** for service accounts
3. **Set resource limits** to prevent resource exhaustion
4. **Configure health checks** for reliable deployments
5. **Use rolling updates** for zero-downtime deployments

### Security
1. **Run as non-root user** in containers
2. **Use read-only root filesystems** where possible
3. **Implement network policies** for micro-segmentation
4. **Rotate secrets regularly** using automated tools
5. **Enable audit logging** for compliance

### Monitoring
1. **Monitor both technical and business metrics**
2. **Set up alerting** for critical issues
3. **Use distributed tracing** for complex operations
4. **Implement log aggregation** for troubleshooting
5. **Regular monitoring review** and optimization

### Performance
1. **Right-size resources** using VPA recommendations
2. **Use HPA** for automatic scaling
3. **Optimize container images** for faster startup
4. **Implement caching strategies** for frequently accessed data
5. **Monitor and optimize** database queries

## 🔗 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [Helm Documentation](https://helm.sh/docs/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [Stellar Documentation](https://developers.stellar.org/)

## 🤝 Support

For deployment support and troubleshooting:
- **Issues**: [GitHub Issues](https://github.com/stellar/hummingbot-connector-v3/issues)
- **Discussions**: [GitHub Discussions](https://github.com/stellar/hummingbot-connector-v3/discussions)
- **Documentation**: [Project Wiki](https://github.com/stellar/hummingbot-connector-v3/wiki)

---

**Note**: This deployment guide assumes a production-ready Kubernetes cluster with proper security, monitoring, and backup procedures in place. Always test deployments in a non-production environment first.