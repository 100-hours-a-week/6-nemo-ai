#!/bin/bash

# =============================================================================
# vLLM FastAPI Monitoring Launcher
# =============================================================================
# 
# Simple launcher script that forwards to the main monitoring setup script
# 
# Usage: ./start-monitoring.sh [OPTIONS]
# =============================================================================

set -euo pipefail

# Check if monitoring directory exists
if [[ ! -d "monitoring" ]]; then
    echo "❌ Error: monitoring/ directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Forward all arguments to the main setup script
echo "🚀 Starting vLLM FastAPI Monitoring Setup..."
echo "📁 Changing to monitoring directory..."

cd monitoring
exec ./setup-monitoring.sh "$@"
