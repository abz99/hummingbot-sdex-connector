#!/bin/bash

# Stellar Hummingbot Connector v3 - Kubernetes Deployment Script
# Phase 4: Production Hardening - Container orchestration deployment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
K8S_DIR="${PROJECT_ROOT}/k8s"

# Default values
ENVIRONMENT="${ENVIRONMENT:-production}"
NAMESPACE="${NAMESPACE:-stellar-${ENVIRONMENT}}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-stellar-registry.io}"
IMAGE_TAG="${IMAGE_TAG:-v3.0.0-$(date +%s)}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_BUILD="${SKIP_BUILD:-false}"
FORCE_DEPLOY="${FORCE_DEPLOY:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Helper functions
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed and configured
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if kustomize is installed
    if ! command -v kustomize &> /dev/null; then
        log_error "kustomize is not installed or not in PATH"
        exit 1
    fi
    
    # Check if docker is installed (if not skipping build)
    if [[ "${SKIP_BUILD}" != "true" ]] && ! command -v docker &> /dev/null; then
        log_error "docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Kubernetes cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if required directories exist
    if [[ ! -d "${K8S_DIR}" ]]; then
        log_error "Kubernetes configuration directory not found: ${K8S_DIR}"
        exit 1
    fi
    
    if [[ ! -d "${K8S_DIR}/overlays/${ENVIRONMENT}" ]]; then
        log_error "Environment overlay not found: ${K8S_DIR}/overlays/${ENVIRONMENT}"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

validate_environment() {
    log_info "Validating environment configuration..."
    
    case "${ENVIRONMENT}" in
        development|staging|production)
            log_info "Deploying to ${ENVIRONMENT} environment"
            ;;
        *)
            log_error "Invalid environment: ${ENVIRONMENT}. Must be one of: development, staging, production"
            exit 1
            ;;
    esac
    
    # Validate critical environment variables for production
    if [[ "${ENVIRONMENT}" == "production" ]]; then
        local required_vars=(
            "STELLAR_SECRET_KEY"
            "DATABASE_URL"
            "REDIS_URL"
            "GRAFANA_ADMIN_PASSWORD"
        )
        
        for var in "${required_vars[@]}"; do
            if [[ -z "${!var:-}" ]]; then
                log_error "Required environment variable not set: ${var}"
                exit 1
            fi
        done
    fi
    
    log_success "Environment validation passed"
}

build_docker_image() {
    if [[ "${SKIP_BUILD}" == "true" ]]; then
        log_info "Skipping Docker image build"
        return 0
    fi
    
    log_info "Building Docker image..."
    
    local dockerfile="${PROJECT_ROOT}/Dockerfile"
    if [[ ! -f "${dockerfile}" ]]; then
        log_warning "Dockerfile not found, creating basic Dockerfile"
        create_dockerfile
    fi
    
    local image_name="${DOCKER_REGISTRY}/stellar-hummingbot-connector:${IMAGE_TAG}"
    
    # Build the image
    docker build \
        --tag "${image_name}" \
        --build-arg ENVIRONMENT="${ENVIRONMENT}" \
        --build-arg VERSION="${IMAGE_TAG}" \
        --file "${dockerfile}" \
        "${PROJECT_ROOT}"
    
    # Push to registry if not local deployment
    if [[ "${DOCKER_REGISTRY}" != "localhost" ]] && [[ "${DOCKER_REGISTRY}" != "local" ]]; then
        log_info "Pushing image to registry..."
        docker push "${image_name}"
    fi
    
    log_success "Docker image built and pushed: ${image_name}"
}

create_dockerfile() {
    log_info "Creating Dockerfile..."
    
    cat > "${PROJECT_ROOT}/Dockerfile" << 'EOF'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r stellar && useradd -r -g stellar stellar
RUN chown -R stellar:stellar /app
USER stellar

# Expose ports
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health/live || exit 1

# Start command
CMD ["python", "-m", "hummingbot.connector.exchange.stellar.main"]
EOF
    
    log_success "Dockerfile created"
}

create_namespace() {
    log_info "Creating namespace: ${NAMESPACE}"
    
    if kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        log_info "Namespace ${NAMESPACE} already exists"
    else
        kubectl create namespace "${NAMESPACE}"
        
        # Add labels to namespace
        kubectl label namespace "${NAMESPACE}" \
            name="${NAMESPACE}" \
            environment="${ENVIRONMENT}" \
            app=stellar-hummingbot-connector
        
        log_success "Namespace ${NAMESPACE} created"
    fi
}

deploy_monitoring_stack() {
    log_info "Deploying monitoring stack..."
    
    local monitoring_namespace="stellar-monitoring"
    
    # Create monitoring namespace
    if ! kubectl get namespace "${monitoring_namespace}" &> /dev/null; then
        kubectl create namespace "${monitoring_namespace}"
        kubectl label namespace "${monitoring_namespace}" name="${monitoring_namespace}"
    fi
    
    # Deploy monitoring components
    kubectl apply -f "${K8S_DIR}/base/monitoring.yaml"
    
    # Wait for monitoring stack to be ready
    log_info "Waiting for monitoring stack to be ready..."
    kubectl wait --namespace="${monitoring_namespace}" \
        --for=condition=ready pod \
        --selector=app=prometheus \
        --timeout=300s
    
    kubectl wait --namespace="${monitoring_namespace}" \
        --for=condition=ready pod \
        --selector=app=grafana \
        --timeout=300s
    
    log_success "Monitoring stack deployed successfully"
}

generate_manifests() {
    log_info "Generating Kubernetes manifests..."
    
    local overlay_dir="${K8S_DIR}/overlays/${ENVIRONMENT}"
    local output_dir="${PROJECT_ROOT}/generated-manifests"
    
    # Create output directory
    mkdir -p "${output_dir}"
    
    # Set image in kustomization
    cd "${overlay_dir}"
    kustomize edit set image "stellar-hummingbot-connector=${DOCKER_REGISTRY}/stellar-hummingbot-connector:${IMAGE_TAG}"
    
    # Generate manifests
    kustomize build "${overlay_dir}" > "${output_dir}/stellar-${ENVIRONMENT}-manifests.yaml"
    
    log_success "Manifests generated: ${output_dir}/stellar-${ENVIRONMENT}-manifests.yaml"
}

validate_manifests() {
    log_info "Validating Kubernetes manifests..."
    
    local manifest_file="${PROJECT_ROOT}/generated-manifests/stellar-${ENVIRONMENT}-manifests.yaml"
    
    if [[ ! -f "${manifest_file}" ]]; then
        log_error "Manifest file not found: ${manifest_file}"
        exit 1
    fi
    
    # Dry run to validate manifests
    kubectl apply --dry-run=client -f "${manifest_file}" > /dev/null
    
    # Check for resource conflicts
    if ! kubectl apply --dry-run=server -f "${manifest_file}" > /dev/null 2>&1; then
        log_warning "Server-side validation detected potential issues"
        if [[ "${FORCE_DEPLOY}" != "true" ]]; then
            log_error "Use --force to override validation issues"
            exit 1
        fi
    fi
    
    log_success "Manifest validation passed"
}

deploy_application() {
    log_info "Deploying application to ${ENVIRONMENT}..."
    
    local manifest_file="${PROJECT_ROOT}/generated-manifests/stellar-${ENVIRONMENT}-manifests.yaml"
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_info "DRY RUN: Would deploy the following resources:"
        kubectl apply --dry-run=client -f "${manifest_file}"
        return 0
    fi
    
    # Apply manifests
    kubectl apply -f "${manifest_file}"
    
    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    kubectl wait --namespace="${NAMESPACE}" \
        --for=condition=progressing \
        deployment/prod-stellar-hummingbot-connector \
        --timeout=600s
    
    kubectl wait --namespace="${NAMESPACE}" \
        --for=condition=available \
        deployment/prod-stellar-hummingbot-connector \
        --timeout=600s
    
    log_success "Application deployed successfully"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check deployment status
    kubectl get deployments --namespace="${NAMESPACE}"
    kubectl get pods --namespace="${NAMESPACE}"
    kubectl get services --namespace="${NAMESPACE}"
    
    # Check pod health
    local pod_name=$(kubectl get pods --namespace="${NAMESPACE}" \
        -l app=stellar-hummingbot-connector \
        -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -n "${pod_name}" ]]; then
        log_info "Checking pod health: ${pod_name}"
        kubectl describe pod "${pod_name}" --namespace="${NAMESPACE}"
        
        # Check logs
        log_info "Recent logs from ${pod_name}:"
        kubectl logs "${pod_name}" --namespace="${NAMESPACE}" --tail=20
    fi
    
    # Test health endpoints
    log_info "Testing health endpoints..."
    if kubectl port-forward --namespace="${NAMESPACE}" \
        "deployment/prod-stellar-hummingbot-connector" 8080:8080 &
    then
        local port_forward_pid=$!
        sleep 5
        
        if curl -f http://localhost:8080/health/ready > /dev/null 2>&1; then
            log_success "Health check endpoint responding"
        else
            log_warning "Health check endpoint not responding"
        fi
        
        kill ${port_forward_pid} 2>/dev/null || true
    fi
    
    log_success "Deployment verification completed"
}

print_access_info() {
    log_info "Deployment Access Information:"
    echo ""
    echo "Namespace: ${NAMESPACE}"
    echo "Environment: ${ENVIRONMENT}"
    echo "Image: ${DOCKER_REGISTRY}/stellar-hummingbot-connector:${IMAGE_TAG}"
    echo ""
    echo "To access the application:"
    echo "  kubectl port-forward --namespace=${NAMESPACE} deployment/prod-stellar-hummingbot-connector 8080:8080"
    echo "  curl http://localhost:8080/health/ready"
    echo ""
    echo "To view logs:"
    echo "  kubectl logs --namespace=${NAMESPACE} -l app=stellar-hummingbot-connector -f"
    echo ""
    echo "To access monitoring:"
    echo "  kubectl port-forward --namespace=stellar-monitoring service/grafana-service 3000:3000"
    echo "  kubectl port-forward --namespace=stellar-monitoring service/prometheus-service 9090:9090"
    echo ""
    echo "To scale the deployment:"
    echo "  kubectl scale --namespace=${NAMESPACE} deployment/prod-stellar-hummingbot-connector --replicas=5"
    echo ""
}

rollback_deployment() {
    log_warning "Rolling back deployment..."
    
    # Get previous revision
    local previous_revision=$(kubectl rollout history \
        --namespace="${NAMESPACE}" \
        deployment/prod-stellar-hummingbot-connector \
        | tail -n 2 | head -n 1 | awk '{print $1}')
    
    if [[ -n "${previous_revision}" ]]; then
        kubectl rollout undo \
            --namespace="${NAMESPACE}" \
            deployment/prod-stellar-hummingbot-connector \
            --to-revision="${previous_revision}"
        
        log_success "Rolled back to revision ${previous_revision}"
    else
        log_error "No previous revision found for rollback"
    fi
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${PROJECT_ROOT}/generated-manifests"
}

# Main execution
main() {
    log_info "Starting Stellar Hummingbot Connector Kubernetes Deployment"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Namespace: ${NAMESPACE}"
    log_info "Image Tag: ${IMAGE_TAG}"
    log_info "Dry Run: ${DRY_RUN}"
    
    # Trap for cleanup
    trap cleanup EXIT
    
    # Execute deployment steps
    check_prerequisites
    validate_environment
    create_namespace
    
    if [[ "${ENVIRONMENT}" == "production" ]] || [[ "${ENVIRONMENT}" == "staging" ]]; then
        deploy_monitoring_stack
    fi
    
    build_docker_image
    generate_manifests
    validate_manifests
    deploy_application
    verify_deployment
    print_access_info
    
    log_success "Deployment completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --namespace|-n)
            NAMESPACE="$2"
            shift 2
            ;;
        --image-tag|-t)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --registry|-r)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --skip-build)
            SKIP_BUILD="true"
            shift
            ;;
        --force)
            FORCE_DEPLOY="true"
            shift
            ;;
        --rollback)
            rollback_deployment
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -e, --environment ENV    Deployment environment (development|staging|production)"
            echo "  -n, --namespace NAME     Kubernetes namespace"
            echo "  -t, --image-tag TAG      Docker image tag"
            echo "  -r, --registry URL       Docker registry URL"
            echo "      --dry-run            Show what would be deployed without applying"
            echo "      --skip-build         Skip Docker image build step"
            echo "      --force              Force deployment despite validation warnings"
            echo "      --rollback           Rollback to previous deployment"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main