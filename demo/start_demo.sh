#!/bin/bash
# QA Monitoring Demo Startup Script
# 
# This script starts the QA monitoring demo environment and provides
# easy access to all demo scenarios and monitoring tools.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local url=$3
    
    if curl -s "$url" > /dev/null 2>&1; then
        print_success "$service_name is running on port $port"
        return 0
    else
        print_warning "$service_name is not accessible on port $port"
        return 1
    fi
}

# Function to display usage
show_usage() {
    cat << EOF
QA Monitoring Demo Environment

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    start         Start the full demo environment
    coverage      Run coverage monitoring demo
    testing       Run test execution demo  
    quality       Run code quality demo
    compliance    Run compliance tracking demo
    alerts        Run alerting scenarios demo
    status        Check service status
    help          Show this help message

OPTIONS:
    --verbose     Enable verbose output

EXAMPLES:
    $0 start                    # Full demo with all scenarios
    $0 coverage --verbose       # Coverage demo with detailed output
    $0 status                   # Check if monitoring services are running

MONITORING DASHBOARDS:
    Grafana:    http://localhost:3000/dashboards
    Prometheus: http://localhost:9090
    Alerts:     http://localhost:9090/alerts

EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Python is available
    if ! command -v python &> /dev/null; then
        print_error "Python is not installed or not in PATH"
        return 1
    fi
    
    # Check if demo script exists
    if [[ ! -f "demo/qa_monitoring_demo.py" ]]; then
        print_error "Demo script not found. Run this script from project root."
        return 1
    fi
    
    # Check if required Python modules can be imported
    if ! python -c "import sys; sys.path.insert(0, '.'); from hummingbot.connector.exchange.stellar.stellar_metrics import StellarMetrics" 2>/dev/null; then
        print_warning "Some Python dependencies may be missing"
    fi
    
    print_success "Prerequisites check completed"
    return 0
}

# Function to check monitoring services
check_services() {
    print_status "Checking monitoring services..."
    
    local all_services_ok=true
    
    # Check Grafana
    if ! check_service "Grafana" "3000" "http://localhost:3000/api/health"; then
        print_warning "Start Grafana with: docker-compose -f observability/docker-compose.yml up -d grafana"
        all_services_ok=false
    fi
    
    # Check Prometheus  
    if ! check_service "Prometheus" "9090" "http://localhost:9090/-/ready"; then
        print_warning "Start Prometheus with: docker-compose -f observability/docker-compose.yml up -d prometheus"
        all_services_ok=false
    fi
    
    if [[ "$all_services_ok" == true ]]; then
        print_success "All monitoring services are running"
        echo ""
        echo "📈 Grafana Dashboard: http://localhost:3000/dashboards"
        echo "🔍 Prometheus Queries: http://localhost:9090"
        echo "🚨 Alert Manager: http://localhost:9090/alerts"
    else
        print_warning "Some monitoring services are not running"
        echo ""
        echo "To start all services:"
        echo "  docker-compose -f observability/docker-compose.yml up -d"
    fi
    
    return 0
}

# Function to run demo scenario
run_demo() {
    local scenario=$1
    local verbose_flag=""
    
    if [[ "$2" == "--verbose" ]]; then
        verbose_flag="--verbose"
    fi
    
    print_status "Starting QA Monitoring Demo: $scenario"
    echo ""
    
    # Run the demo
    if python demo/qa_monitoring_demo.py --scenario "$scenario" $verbose_flag; then
        echo ""
        print_success "Demo completed successfully!"
        echo ""
        echo "📊 View results in:"
        echo "  • Grafana: http://localhost:3000/dashboards"
        echo "  • Prometheus: http://localhost:9090"
        echo "  • Alerts: http://localhost:9090/alerts"
    else
        echo ""
        print_error "Demo failed. Check logs above for details."
        return 1
    fi
}

# Main script logic
main() {
    local command=${1:-"help"}
    local option=${2:-""}
    
    # Change to project root if not already there
    if [[ ! -f "demo/qa_monitoring_demo.py" && -f "../demo/qa_monitoring_demo.py" ]]; then
        cd ..
    fi
    
    case $command in
        "start"|"full")
            check_prerequisites && run_demo "full" "$option"
            ;;
        "coverage")
            check_prerequisites && run_demo "coverage" "$option"
            ;;
        "testing")
            check_prerequisites && run_demo "testing" "$option"
            ;;
        "quality")  
            check_prerequisites && run_demo "quality" "$option"
            ;;
        "compliance")
            check_prerequisites && run_demo "compliance" "$option"
            ;;
        "alerts")
            check_prerequisites && run_demo "alerts" "$option"
            ;;
        "status")
            check_services
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"