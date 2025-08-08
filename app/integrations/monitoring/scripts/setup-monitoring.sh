#!/bin/bash

# =============================================================================
# vLLM FastAPI Monitoring Setup Script
# =============================================================================
# 
# This script sets up a complete monitoring stack including:
# - Prometheus (metrics collection)
# - Grafana (visualization) 
# - Alertmanager (notifications)
# - Node Exporter (system metrics)
# - Optional GPU monitoring
#
# Usage: ./setup-monitoring.sh [OPTIONS]
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

readonly SCRIPT_VERSION="2.0.0"
readonly DEFAULT_MONITORING_DIR="."

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Configuration variables
MONITORING_DIR="${DEFAULT_MONITORING_DIR}"
GRAFANA_ADMIN_USER=""
GRAFANA_ADMIN_PASSWORD=""
PROMETHEUS_RETENTION_TIME=""
ENABLE_GPU_MONITORING=false
ENABLE_ALERTING=true
PRODUCTION_MODE=false
COMPOSE_FILE="docker-compose.monitoring.yml"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_info() { echo -e "${BLUE}ℹ️  $*${NC}"; }
print_success() { echo -e "${GREEN}✅ $*${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $*${NC}"; }
print_error() { echo -e "${RED}❌ $*${NC}"; }
print_step() { echo -e "${CYAN}🔧 $*${NC}"; }

print_header() {
    echo -e "${CYAN}"
    echo "============================================================================="
    echo " $*"
    echo "============================================================================="
    echo -e "${NC}"
}

command_exists() { command -v "$1" >/dev/null 2>&1; }

wait_for_service() {
    local url="$1" service_name="$2" max_attempts=30 attempt=1
    
    print_step "Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_error "$service_name failed to start within $(($max_attempts * 2)) seconds"
    return 1
}

# =============================================================================
# HELP AND ARGUMENT PARSING
# =============================================================================

show_help() {
    cat << EOF
vLLM FastAPI Monitoring Setup v${SCRIPT_VERSION}

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    --gpu               Enable GPU monitoring with DCGM exporter
    --production        Use production configuration with security hardening
    --alerting          Enable alerting (default: enabled)
    --no-alerting       Disable alerting
    --user USERNAME     Set Grafana admin username
    --password PASS     Set Grafana admin password
    --status            Show status of monitoring services
    --stop              Stop all monitoring services
    --logs              Show logs from all services

EXAMPLES:
    $0                          # Basic setup with alerting
    $0 --gpu --production       # Production setup with GPU monitoring
    $0 --status                 # Check service status
    $0 --stop                   # Stop all services

SERVICES ACCESS:
    - Grafana:       http://localhost:3000
    - Prometheus:    http://localhost:9090
    - Alertmanager:  http://localhost:9093
    - Metrics:       http://localhost:8000/metrics
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_help; exit 0 ;;
            --gpu) ENABLE_GPU_MONITORING=true; shift ;;
            --production) PRODUCTION_MODE=true; COMPOSE_FILE="docker-compose.monitoring.prod.yml"; shift ;;
            --alerting) ENABLE_ALERTING=true; shift ;;
            --no-alerting) ENABLE_ALERTING=false; shift ;;
            --user) GRAFANA_ADMIN_USER="$2"; shift 2 ;;
            --password) GRAFANA_ADMIN_PASSWORD="$2"; shift 2 ;;
            --status) show_status; exit $? ;;
            --stop) stop_services; exit $? ;;
            --logs) show_logs; exit $? ;;
            *) print_error "Unknown option: $1"; echo "Use --help for usage."; exit 1 ;;
        esac
    done
}

# =============================================================================
# SERVICE MANAGEMENT
# =============================================================================

show_status() {
    print_header "MONITORING SERVICES STATUS"
    
    local services=(
        "nemo-prometheus:Prometheus:9090"
        "nemo-grafana:Grafana:3000"
        "nemo-alertmanager:Alertmanager:9093"
        "nemo-node-exporter:Node Exporter:9100"
    )
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r container_name service_name port <<< "$service_info"
        
        if docker ps --format "table {{.Names}}" | grep -q "^${container_name}$"; then
            local status="Running"
            if curl -sf "http://localhost:${port}" >/dev/null 2>&1 || 
               curl -sf "http://localhost:${port}/api/health" >/dev/null 2>&1 ||
               curl -sf "http://localhost:${port}/-/healthy" >/dev/null 2>&1; then
                status="Running & Healthy"
                print_success "${service_name}: ${status}"
            else
                status="Running (Not Responding)"
                print_warning "${service_name}: ${status}"
            fi
        else
            print_error "${service_name}: Stopped"
        fi
    done
    
    # Check FastAPI app
    if curl -sf "http://localhost:8000/health" >/dev/null 2>&1; then
        print_success "FastAPI App: Running & Healthy"
    elif curl -sf "http://localhost:8000" >/dev/null 2>&1; then
        print_warning "FastAPI App: Running (Health check unavailable)"
    else
        print_error "FastAPI App: Not accessible"
    fi
}

stop_services() {
    print_header "STOPPING MONITORING SERVICES"
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        print_step "Stopping services..."
        docker-compose -f "$COMPOSE_FILE" down
        print_success "All monitoring services stopped"
    else
        print_error "Compose file $COMPOSE_FILE not found"
        exit 1
    fi
}

show_logs() {
    print_header "MONITORING SERVICES LOGS"
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" logs -f --tail=50
    else
        print_error "Compose file $COMPOSE_FILE not found"
        exit 1
    fi
}

# =============================================================================
# SETUP FUNCTIONS
# =============================================================================

load_environment() {
    print_step "Loading environment configuration..."
    
    # Look for .env file in multiple locations
    local env_files=(
        "../../../../.env"  # From docker directory
        "../../../.env"     # From scripts directory  
        "../../.env"        # From monitoring directory
        "../.env"           # One level up
        ".env"              # Current directory
    )
    
    local env_found=false
    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            set -a
            # shellcheck source=/dev/null
            source "$env_file"
            set +a
            print_success "Loaded configuration from $env_file"
            env_found=true
            break
        fi
    done
    
    if [[ "$env_found" == false ]]; then
        print_warning ".env file not found in expected locations, using defaults"
    fi
    
    # Set required environment variables - fail if not set
    if [[ -z "$GRAFANA_ADMIN_USER" ]]; then
        print_error "GRAFANA_ADMIN_USER not set in .env file"
        exit 1
    fi
    
    if [[ -z "$GRAFANA_ADMIN_PASSWORD" ]]; then
        print_error "GRAFANA_ADMIN_PASSWORD not set in .env file" 
        exit 1
    fi
    
    # Set other defaults only if not already set
    PROMETHEUS_RETENTION_TIME="${PROMETHEUS_RETENTION_TIME:-15d}"
    
    # Export for docker-compose
    export GRAFANA_ADMIN_USER GRAFANA_ADMIN_PASSWORD PROMETHEUS_RETENTION_TIME
}

validate_prerequisites() {
    print_step "Validating prerequisites..."
    
    local errors=0
    for cmd in docker docker-compose curl; do
        if ! command_exists "$cmd"; then
            print_error "$cmd is not installed"
            ((errors++))
        fi
    done
    
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        ((errors++))
    fi
    
    if [[ $errors -gt 0 ]]; then
        print_error "$errors prerequisite check(s) failed"
        exit 1
    fi
    
    print_success "All prerequisites validated"
}

create_directories() {
    print_step "Creating monitoring directories..."
    
    local dirs=(
        "prometheus-data"
        "grafana-data"
        "grafana-logs"
        "alertmanager-data"
        "backups"
        "grafana-provisioning/datasources"
        "grafana-provisioning/dashboards"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
    done
    
    # Set permissions for Docker containers on Linux
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_step "Setting directory permissions..."
        sudo chown -R 65534:65534 "prometheus-data" 2>/dev/null || true
        sudo chown -R 472:472 "grafana-data" "grafana-logs" 2>/dev/null || true
    fi
    
    print_success "Monitoring directories created"
}

check_application() {
    print_step "Checking FastAPI application..."
    
    if curl -sf "http://localhost:8000/health" >/dev/null 2>&1; then
        print_success "FastAPI application is running and healthy"
        
        if curl -sf "http://localhost:8000/metrics" >/dev/null 2>&1; then
            print_success "Metrics endpoint is accessible"
        else
            print_warning "Metrics endpoint not found at /metrics"
        fi
    elif curl -sf "http://localhost:8000" >/dev/null 2>&1; then
        print_success "FastAPI application is running"
    else
        print_warning "FastAPI app not accessible. You can start monitoring anyway."
    fi
}

check_dependencies() {
    print_step "Checking Python dependencies..."
    
    if python3 -c "import prometheus_fastapi_instrumentator, prometheus_client, psutil" 2>/dev/null; then
        print_success "Required Python packages are installed"
    else
        print_warning "Some monitoring dependencies may be missing"
        print_info "Install with: pip install prometheus-fastapi-instrumentator prometheus-client psutil"
    fi
    
    if [[ "$ENABLE_GPU_MONITORING" == true ]]; then
        if python3 -c "import GPUtil" 2>/dev/null; then
            print_success "GPU monitoring dependencies available"
        else
            print_warning "GPUtil not found. Disabling GPU monitoring"
            ENABLE_GPU_MONITORING=false
        fi
    fi
}

validate_gpu_requirements() {
    if [[ "$ENABLE_GPU_MONITORING" != true ]]; then
        return 0
    fi
    
    print_step "Validating GPU monitoring requirements..."
    
    if ! command_exists nvidia-smi; then
        print_warning "nvidia-smi not found. Disabling GPU monitoring"
        ENABLE_GPU_MONITORING=false
        return 0
    fi
    
    if ! docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi >/dev/null 2>&1; then
        print_warning "Docker GPU access not working. Disabling GPU monitoring"
        ENABLE_GPU_MONITORING=false
        return 0
    fi
    
    print_success "GPU monitoring requirements validated"
}

start_services() {
    print_step "Starting monitoring services..."
    
    local compose_cmd="docker-compose -f $COMPOSE_FILE"
    local profiles=()
    
    if [[ "$ENABLE_GPU_MONITORING" == true ]]; then
        profiles+=("--profile" "gpu")
    fi
    
    if [[ "$ENABLE_ALERTING" == true ]]; then
        profiles+=("--profile" "alerting")
    fi
    
    print_info "Using configuration: $COMPOSE_FILE"
    if [[ ${#profiles[@]} -gt 0 ]]; then
        print_info "Active profiles: ${profiles[*]}"
    fi
    
    $compose_cmd "${profiles[@]}" up -d
    print_success "Services started successfully"
}

verify_services() {
    print_header "VERIFYING SERVICES"
    
    local services=(
        "http://localhost:9090/-/healthy:Prometheus"
        "http://localhost:3000/api/health:Grafana"
    )
    
    if [[ "$ENABLE_ALERTING" == true ]]; then
        services+=("http://localhost:9093/-/healthy:Alertmanager")
    fi
    
    local failed_services=0
    for service_info in "${services[@]}"; do
        local url="${service_info%%:*}"
        local name="${service_info##*:}"
        
        if wait_for_service "$url" "$name"; then
            continue
        else
            print_error "$name health check failed"
            ((failed_services++))
        fi
    done
    
    if [[ $failed_services -eq 0 ]]; then
        print_success "All services are healthy"
    else
        print_warning "$failed_services service(s) failed health checks"
    fi
}

show_completion_summary() {
    print_header "SETUP COMPLETE!"
    
    cat << EOF

🎉 ${GREEN}Monitoring stack is now running!${NC}

📊 ${CYAN}Service URLs:${NC}
   • Grafana:      http://localhost:3000
     Username:     ${GRAFANA_ADMIN_USER}
     Password:     ${GRAFANA_ADMIN_PASSWORD}
   
   • Prometheus:   http://localhost:9090
   • Metrics:      http://localhost:8000/metrics

EOF

    if [[ "$ENABLE_ALERTING" == true ]]; then
        echo "   • Alertmanager: http://localhost:9093"
    fi
    
    if [[ "$ENABLE_GPU_MONITORING" == true ]]; then
        echo "   • GPU Metrics:  http://localhost:9400/metrics"
    fi
    
    cat << EOF

🔧 ${CYAN}Management Commands:${NC}
   • Status:       $0 --status
   • Stop:         $0 --stop  
   • Logs:         $0 --logs
   • Restart:      docker-compose -f ${COMPOSE_FILE} restart

📈 ${CYAN}Next Steps:${NC}
   1. Import Grafana dashboard from monitoring/grafana-provisioning/dashboards/
   2. Start your FastAPI application to see metrics
   3. Configure alert notification channels
   4. Review docs/MONITORING.md for detailed usage

EOF

    if [[ "$PRODUCTION_MODE" == true ]]; then
        echo -e "🔒 ${YELLOW}Production mode enabled with enhanced security${NC}"
    fi
    
    echo
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    print_header "vLLM FastAPI Monitoring Setup v${SCRIPT_VERSION}"
    
    parse_arguments "$@"
    
    print_info "Configuration:"
    print_info "  GPU Monitoring: $ENABLE_GPU_MONITORING"
    print_info "  Alerting: $ENABLE_ALERTING" 
    print_info "  Production Mode: $PRODUCTION_MODE"
    echo
    
    load_environment
    validate_prerequisites
    check_application
    check_dependencies
    validate_gpu_requirements
    create_directories
    start_services
    verify_services
    show_completion_summary
    
    print_success "Monitoring setup completed successfully! 🚀"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
