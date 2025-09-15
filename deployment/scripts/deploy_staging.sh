#!/bin/bash
#
# Staging Deployment Script
# Stellar Hummingbot Connector v3.0
#
# Deploys the connector to staging environment for final validation.
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"
NAMESPACE="stellar-hummingbot"
IMAGE_TAG="${IMAGE_TAG:-staging-$(date +%Y%m%d-%H%M%S)}"
ENVIRONMENT="${ENVIRONMENT:-staging}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

print_header() {
    echo -e "\n${BLUE}================================================================================================${NC}"
    echo -e "${BLUE}🚀 STAGING DEPLOYMENT - Stellar Hummingbot Connector v3.0${NC}"
    echo -e "${BLUE}================================================================================================${NC}\n"
}

print_section() {
    echo -e "\n${YELLOW}📋 $1${NC}"
    echo -e "${YELLOW}$(printf '=%.0s' {1..80})${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_section "CHECKING PREREQUISITES"
    
    local missing_tools=()
    local tools=("kubectl" "docker" "python3")
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        else
            print_success "$tool is available"
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check if we can access Kubernetes
    if kubectl cluster-info &>/dev/null; then
        CURRENT_CONTEXT=$(kubectl config current-context)
        print_success "Kubernetes accessible - Context: $CURRENT_CONTEXT"
        
        # Warn if using production context
        if [[ "$CURRENT_CONTEXT" =~ production ]]; then
            print_warning "You appear to be using a production Kubernetes context!"
            print_warning "Please ensure you want to deploy to: $CURRENT_CONTEXT"
            read -p "Continue? (yes/no): " -r
            if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
                print_error "Deployment cancelled by user"
                exit 1
            fi
        fi
    else
        print_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    log "Prerequisites check completed"
}

# Run security validation
run_security_validation() {
    print_section "RUNNING SECURITY VALIDATION"
    
    log "Running comprehensive security validation..."
    
    if [ -f "$DEPLOYMENT_DIR/security/security_validation.py" ]; then
        cd "$DEPLOYMENT_DIR/security"
        
        if python3 security_validation.py; then
            print_success "Security validation passed"
        else
            print_error "Security validation failed - deployment aborted"
            exit 1
        fi
    else
        print_warning "Security validation script not found - proceeding with caution"
    fi
    
    log "Security validation completed"
}

# Build and push container image
build_and_push_image() {
    print_section "BUILDING CONTAINER IMAGE"
    
    log "Building production container image..."
    
    cd "$PROJECT_ROOT"
    
    # Build the image
    if docker build -t "stellar-hummingbot-connector:$IMAGE_TAG" -f "$DEPLOYMENT_DIR/docker/Dockerfile.production" .; then
        print_success "Container image built successfully"
    else
        print_error "Failed to build container image"
        exit 1
    fi
    
    # Tag for registry (if configured)
    if [ -n "${REGISTRY:-}" ]; then
        docker tag "stellar-hummingbot-connector:$IMAGE_TAG" "$REGISTRY/stellar-hummingbot-connector:$IMAGE_TAG"
        
        # Push to registry
        log "Pushing image to registry..."
        if docker push "$REGISTRY/stellar-hummingbot-connector:$IMAGE_TAG"; then
            print_success "Image pushed to registry: $REGISTRY/stellar-hummingbot-connector:$IMAGE_TAG"
        else
            print_error "Failed to push image to registry"
            exit 1
        fi
    else
        print_warning "No registry configured - using local image"
    fi
    
    log "Container image preparation completed"
}

# Create namespace and basic resources
create_namespace() {
    print_section "CREATING NAMESPACE AND BASIC RESOURCES"
    
    log "Creating namespace: $NAMESPACE"
    
    # Apply namespace configuration
    if kubectl apply -f "$DEPLOYMENT_DIR/kubernetes/namespace.yaml"; then
        print_success "Namespace configuration applied"
    else
        print_error "Failed to apply namespace configuration"
        exit 1
    fi
    
    # Apply RBAC configurations
    if kubectl apply -f "$DEPLOYMENT_DIR/kubernetes/rbac.yaml"; then
        print_success "RBAC configurations applied"
    else
        print_error "Failed to apply RBAC configurations"
        exit 1
    fi
    
    log "Basic resources created"
}

# Deploy configuration and secrets
deploy_configuration() {
    print_section "DEPLOYING CONFIGURATION AND SECRETS"
    
    log "Applying configuration resources..."
    
    # Create ConfigMap (if it exists)
    if [ -f "$DEPLOYMENT_DIR/kubernetes/configmap.yaml" ]; then
        kubectl apply -f "$DEPLOYMENT_DIR/kubernetes/configmap.yaml" || true
        print_success "ConfigMap applied"
    fi
    
    # Apply secrets (external secrets will be managed by operator)
    if kubectl apply -f "$DEPLOYMENT_DIR/security/secrets.yaml"; then
        print_success "Secrets configuration applied"
    else
        print_warning "Secrets configuration failed - may need manual intervention"
    fi
    
    log "Configuration deployment completed"
}

# Deploy monitoring stack
deploy_monitoring() {
    print_section "DEPLOYING MONITORING STACK"
    
    log "Deploying Prometheus and Grafana..."
    
    # Deploy Prometheus
    if kubectl apply -f "$DEPLOYMENT_DIR/monitoring/prometheus.yaml"; then
        print_success "Prometheus deployed"
    else
        print_warning "Prometheus deployment failed"
    fi
    
    # Deploy Grafana
    if kubectl apply -f "$DEPLOYMENT_DIR/monitoring/grafana.yaml"; then
        print_success "Grafana deployed"
    else
        print_warning "Grafana deployment failed"
    fi
    
    # Wait for monitoring stack to be ready
    log "Waiting for monitoring stack to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n "$NAMESPACE" || true
    kubectl wait --for=condition=available --timeout=300s deployment/grafana -n "$NAMESPACE" || true
    
    print_success "Monitoring stack deployment completed"
    log "Monitoring deployment completed"
}

# Deploy main application
deploy_application() {
    print_section "DEPLOYING MAIN APPLICATION"
    
    log "Preparing application deployment..."
    
    # Update image tag in deployment manifest
    local temp_deployment="/tmp/deployment-staging.yaml"
    sed "s|stellar-hummingbot-connector:3.0|stellar-hummingbot-connector:$IMAGE_TAG|g" \
        "$DEPLOYMENT_DIR/kubernetes/deployment-production.yaml" > "$temp_deployment"
    
    # Apply application deployment
    if kubectl apply -f "$temp_deployment"; then
        print_success "Application deployment applied"
    else
        print_error "Failed to apply application deployment"
        exit 1
    fi
    
    # Wait for deployment to be ready
    log "Waiting for application deployment to be ready..."
    if kubectl rollout status deployment/stellar-hummingbot-connector -n "$NAMESPACE" --timeout=600s; then
        print_success "Application deployment is ready"
    else
        print_error "Application deployment failed to become ready"
        
        # Show pod status for debugging
        echo -e "\n${YELLOW}Pod status for debugging:${NC}"
        kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=stellar-hummingbot-connector
        kubectl describe pods -n "$NAMESPACE" -l app.kubernetes.io/name=stellar-hummingbot-connector
        
        exit 1
    fi
    
    # Cleanup temporary file
    rm -f "$temp_deployment"
    
    log "Application deployment completed"
}

# Run health checks
run_health_checks() {
    print_section "RUNNING HEALTH CHECKS"
    
    log "Performing health checks..."
    
    # Get service information
    local service_ip=$(kubectl get service stellar-hummingbot-service -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "")
    
    if [ -n "$service_ip" ]; then
        print_success "Service is available at: $service_ip"
        
        # Test health endpoints (using port-forward for testing)
        local health_check_passed=true
        
        # Port forward to test endpoints
        kubectl port-forward service/stellar-hummingbot-service -n "$NAMESPACE" 8080:8080 &
        local port_forward_pid=$!
        
        # Wait for port forward to establish
        sleep 5
        
        # Test health endpoint
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health | grep -q "200"; then
            print_success "Health endpoint responding"
        else
            print_warning "Health endpoint not responding"
            health_check_passed=false
        fi
        
        # Test metrics endpoint
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/metrics | grep -q "200"; then
            print_success "Metrics endpoint responding"
        else
            print_warning "Metrics endpoint not responding"
            health_check_passed=false
        fi
        
        # Test readiness endpoint
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ready | grep -q "200"; then
            print_success "Readiness endpoint responding"
        else
            print_warning "Readiness endpoint not responding"
            health_check_passed=false
        fi
        
        # Clean up port forward
        kill $port_forward_pid 2>/dev/null || true
        
        if $health_check_passed; then
            print_success "All health checks passed"
        else
            print_warning "Some health checks failed - investigate logs"
        fi
    else
        print_warning "Unable to get service IP"
    fi
    
    log "Health checks completed"
}

# Display deployment summary
show_deployment_summary() {
    print_section "DEPLOYMENT SUMMARY"
    
    echo -e "\n📊 **Deployment Details:**"
    echo -e "   Environment: $ENVIRONMENT"
    echo -e "   Namespace: $NAMESPACE" 
    echo -e "   Image Tag: $IMAGE_TAG"
    echo -e "   Timestamp: $(date)"
    
    echo -e "\n🔍 **Resource Status:**"
    kubectl get all -n "$NAMESPACE" -l app.kubernetes.io/name=stellar-hummingbot-connector
    
    echo -e "\n📊 **Pod Details:**"
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=stellar-hummingbot-connector -o wide
    
    echo -e "\n🌐 **Service Information:**"
    kubectl get services -n "$NAMESPACE"
    
    echo -e "\n📋 **Access Information:**"
    local service_ip=$(kubectl get service stellar-hummingbot-service -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "N/A")
    echo -e "   Application Service: $service_ip:8080"
    echo -e "   Health Check: http://$service_ip:8080/health"
    echo -e "   Metrics: http://$service_ip:8080/metrics"
    
    # Monitoring services
    local grafana_ip=$(kubectl get service grafana-service -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "N/A")
    local prometheus_ip=$(kubectl get service prometheus-service -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "N/A")
    
    echo -e "   Grafana: http://$grafana_ip:3000"
    echo -e "   Prometheus: http://$prometheus_ip:9090"
    
    echo -e "\n💡 **Next Steps:**"
    echo -e "   • Monitor application logs: kubectl logs -f deployment/stellar-hummingbot-connector -n $NAMESPACE"
    echo -e "   • Access Grafana dashboards for monitoring"
    echo -e "   • Run integration tests against staging environment"
    echo -e "   • Review application metrics and performance"
    
    log "Deployment summary displayed"
}

# Main execution function
main() {
    print_header
    
    log "Starting staging deployment for Stellar Hummingbot Connector v3.0..."
    
    # Execute deployment steps
    check_prerequisites
    run_security_validation
    # build_and_push_image  # Uncomment when registry is available
    create_namespace
    deploy_configuration
    deploy_monitoring
    deploy_application
    run_health_checks
    show_deployment_summary
    
    print_section "DEPLOYMENT COMPLETE"
    
    print_success "Staging deployment completed successfully! 🎉"
    print_success "Environment: $ENVIRONMENT"
    print_success "Namespace: $NAMESPACE"
    print_success "Image: stellar-hummingbot-connector:$IMAGE_TAG"
    
    log "Staging deployment completed successfully"
}

# Execute main function
main "$@"