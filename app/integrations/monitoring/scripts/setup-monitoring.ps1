# =============================================================================
# vLLM FastAPI Monitoring Setup Script (PowerShell)
# =============================================================================
# 
# This script sets up a complete monitoring stack including:
# - Prometheus (metrics collection)
# - Grafana (visualization) 
# - Alertmanager (notifications)
# - Node Exporter (system metrics)
# - Optional GPU monitoring
#
# Usage: .\setup-monitoring.ps1 [OPTIONS]
# =============================================================================

[CmdletBinding()]
param(
    [switch]$Help,
    [switch]$Gpu,
    [switch]$Production,
    [switch]$Alerting = $true,
    [switch]$NoAlerting,
    [string]$User,
    [string]$Password,
    [switch]$Status,
    [switch]$Stop,
    [switch]$Logs
)

# Configuration variables
$SCRIPT_VERSION = "2.0.0"
$ENABLE_GPU_MONITORING = $Gpu
$ENABLE_ALERTING = $Alerting -and -not $NoAlerting
$PRODUCTION_MODE = $Production
$COMPOSE_FILE = if ($Production) { "docker-compose.monitoring.prod.yml" } else { "docker-compose.monitoring.yml" }

# Main execution function
function Main {
    if ($Help) {
        Write-Host @"
vLLM FastAPI Monitoring Setup v$SCRIPT_VERSION

USAGE:
    .\setup-monitoring.ps1 [OPTIONS]

OPTIONS:
    -Help               Show this help message
    -Gpu                Enable GPU monitoring
    -Production         Use production configuration
    -Status             Show status of monitoring services
    -Stop               Stop all monitoring services
    -Logs               Show logs from all services

EXAMPLES:
    .\setup-monitoring.ps1                          # Basic setup
    .\setup-monitoring.ps1 -Gpu -Production         # Production setup with GPU monitoring
    .\setup-monitoring.ps1 -Status                  # Check service status

SERVICES ACCESS:
    - Grafana:       http://localhost:3000
    - Prometheus:    http://localhost:9090
    - Alertmanager:  http://localhost:9093
    - Metrics:       http://localhost:8000/metrics
"@
        exit 0
    }
    
    if ($Status) {
        Write-Host "Checking monitoring services status..." -ForegroundColor Cyan
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Where-Object { $_ -match "nemo-|prometheus|grafana|alertmanager" }
        exit 0
    }
    
    if ($Stop) {
        Write-Host "Stopping monitoring services..." -ForegroundColor Yellow
        if (Test-Path $COMPOSE_FILE) {
            docker-compose -f $COMPOSE_FILE down
            Write-Host "All monitoring services stopped" -ForegroundColor Green
        } else {
            Write-Host "Compose file $COMPOSE_FILE not found" -ForegroundColor Red
        }
        exit 0
    }
    
    if ($Logs) {
        if (Test-Path $COMPOSE_FILE) {
            docker-compose -f $COMPOSE_FILE logs -f --tail=50
        } else {
            Write-Host "Compose file $COMPOSE_FILE not found" -ForegroundColor Red
        }
        exit 0
    }
    
    # Main setup process
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host " vLLM FastAPI Monitoring Setup v$SCRIPT_VERSION" -ForegroundColor Cyan
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Configuration:" -ForegroundColor Blue
    Write-Host "  GPU Monitoring: $ENABLE_GPU_MONITORING" -ForegroundColor Blue
    Write-Host "  Alerting: $ENABLE_ALERTING" -ForegroundColor Blue
    Write-Host "  Production Mode: $PRODUCTION_MODE" -ForegroundColor Blue
    Write-Host ""
    
    # Load environment configuration
    Write-Host "Loading environment configuration..." -ForegroundColor Cyan
    
    # Look for .env file in multiple locations
    $envFiles = @(
        "../../../../.env",  # From docker directory
        "../../../.env",     # From scripts directory  
        "../../.env",        # From monitoring directory
        "../.env",           # One level up
        ".env"               # Current directory
    )
    
    $envFound = $false
    foreach ($envFile in $envFiles) {
        if (Test-Path $envFile) {
            Get-Content $envFile | ForEach-Object {
                if ($_ -match "^([^=]+)=(.*)$") {
                    [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
                }
            }
            Write-Host "✅ Loaded configuration from $envFile" -ForegroundColor Green
            $envFound = $true
            break
        }
    }
    
    if (-not $envFound) {
        Write-Host "⚠️ .env file not found in expected locations, using defaults" -ForegroundColor Yellow
    }
    
    # Check prerequisites
    Write-Host "Validating prerequisites..." -ForegroundColor Cyan
    $errors = 0
    
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Docker is not installed" -ForegroundColor Red
        $errors++
    }
    
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Docker Compose is not installed" -ForegroundColor Red
        $errors++
    }
    
    if ($errors -gt 0) {
        Write-Host "❌ $errors prerequisite check(s) failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ All prerequisites validated" -ForegroundColor Green
    
    # Create directories
    Write-Host "Creating monitoring directories..." -ForegroundColor Cyan
    $dirs = @("prometheus-data", "grafana-data", "grafana-logs", "alertmanager-data", "backups")
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    Write-Host "✅ Monitoring directories created" -ForegroundColor Green
    
    # Start services
    Write-Host "Starting monitoring services..." -ForegroundColor Cyan
    Write-Host "Using configuration: $COMPOSE_FILE" -ForegroundColor Blue
    
    docker-compose -f $COMPOSE_FILE up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Services started successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to start services" -ForegroundColor Red
        exit 1
    }
    
    # Show completion summary
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host " SETUP COMPLETE!" -ForegroundColor Cyan
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🎉 Monitoring stack is now running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Service URLs:" -ForegroundColor Cyan
    Write-Host "   • Grafana:      http://localhost:3000"
    Write-Host "   • Prometheus:   http://localhost:9090"
    Write-Host "   • Metrics:      http://localhost:8000/metrics"
    if ($ENABLE_ALERTING) {
        Write-Host "   • Alertmanager: http://localhost:9093"
    }
    Write-Host ""
    Write-Host "🔧 Management Commands:" -ForegroundColor Cyan
    Write-Host "   • Status:       .\setup-monitoring.ps1 -Status"
    Write-Host "   • Stop:         .\setup-monitoring.ps1 -Stop"
    Write-Host "   • Logs:         .\setup-monitoring.ps1 -Logs"
    Write-Host ""
    Write-Host "✅ Monitoring setup completed successfully! 🚀" -ForegroundColor Green
}

# Run main function
Main
