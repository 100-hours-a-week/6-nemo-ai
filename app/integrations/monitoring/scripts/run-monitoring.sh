#!/bin/bash

# =============================================================================
# vLLM FastAPI Monitoring Runner Script (Bash)
# =============================================================================
# This is a convenience script to run monitoring from the app/integrations/monitoring directory
# It changes to the docker directory and runs the setup script

set -euo pipefail

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

show_help() {
    cat << EOF
vLLM FastAPI Monitoring Runner Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    --gpu               Enable GPU monitoring
    --production        Use production configuration
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

# Initialize variables
HELP=false
GPU=false
PRODUCTION=false
ALERTING=true
NO_ALERTING=false
USER=""
PASSWORD=""
STATUS=false
STOP=false
LOGS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            HELP=true
            shift
            ;;
        --gpu)
            GPU=true
            shift
            ;;
        --production)
            PRODUCTION=true
            shift
            ;;
        --alerting)
            ALERTING=true
            shift
            ;;
        --no-alerting)
            NO_ALERTING=true
            ALERTING=false
            shift
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        --password)
            PASSWORD="$2"
            shift 2
            ;;
        --status)
            STATUS=true
            shift
            ;;
        --stop)
            STOP=true
            shift
            ;;
        --logs)
            LOGS=true
            shift
            ;;
        *)
            echo "❌ Unknown option: $1" >&2
            echo "Use --help for usage." >&2
            exit 1
            ;;
    esac
done

# =============================================================================
# DIRECTORY VALIDATION
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")/docker"
SETUP_SCRIPT="$SCRIPT_DIR/setup-monitoring.sh"

# Check if we're in the right directory structure
if [[ ! -d "$DOCKER_DIR" ]]; then
    echo "❌ Docker directory not found. Please run this script from app/integrations/monitoring/" >&2
    exit 1
fi

if [[ ! -f "$SETUP_SCRIPT" ]]; then
    echo "❌ Setup script not found at $SETUP_SCRIPT" >&2
    exit 1
fi

# Make sure setup script is executable
if [[ ! -x "$SETUP_SCRIPT" ]]; then
    echo "🔧 Making setup script executable..."
    chmod +x "$SETUP_SCRIPT"
fi

# =============================================================================
# MAIN EXECUTION
# =============================================================================

# Change to docker directory
ORIGINAL_DIR="$(pwd)"
cd "$DOCKER_DIR"

# Function to restore original directory on exit
cleanup() {
    cd "$ORIGINAL_DIR"
}
trap cleanup EXIT

# Build arguments for the setup script
setup_args=()

if [[ "$HELP" == true ]]; then
    setup_args+=("--help")
fi

if [[ "$GPU" == true ]]; then
    setup_args+=("--gpu")
fi

if [[ "$PRODUCTION" == true ]]; then
    setup_args+=("--production")
fi

if [[ "$NO_ALERTING" == true ]]; then
    setup_args+=("--no-alerting")
elif [[ "$ALERTING" == true ]]; then
    setup_args+=("--alerting")
fi

if [[ -n "$USER" ]]; then
    setup_args+=("--user" "$USER")
fi

if [[ -n "$PASSWORD" ]]; then
    setup_args+=("--password" "$PASSWORD")
fi

if [[ "$STATUS" == true ]]; then
    setup_args+=("--status")
fi

if [[ "$STOP" == true ]]; then
    setup_args+=("--stop")
fi

if [[ "$LOGS" == true ]]; then
    setup_args+=("--logs")
fi

# Run the setup script with all arguments
"$SETUP_SCRIPT" "${setup_args[@]}"
