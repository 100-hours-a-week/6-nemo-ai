# =============================================================================
# Quick Start Script - Redirects to New Monitoring Location
# =============================================================================
# This script redirects to the new monitoring setup in app/integrations/monitoring

Write-Host ""
Write-Host "=============================================================================" -ForegroundColor Cyan
Write-Host " NEMO AI Monitoring - Quick Start" -ForegroundColor Cyan  
Write-Host "=============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📍 " -NoNewline -ForegroundColor Blue
Write-Host "Monitoring has been refactored to: " -NoNewline -ForegroundColor Blue
Write-Host "app/integrations/monitoring/" -ForegroundColor Yellow

Write-Host ""
Write-Host "🚀 " -NoNewline -ForegroundColor Green
Write-Host "To start monitoring, use one of these commands:" -ForegroundColor Green
Write-Host ""
Write-Host "   # Option 1: Use the convenience script (recommended)"
Write-Host "   .\app\integrations\monitoring\run-monitoring.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # Option 2: Navigate to the monitoring directory"
Write-Host "   cd app\integrations\monitoring\docker" -ForegroundColor Cyan
Write-Host "   ..\scripts\setup-monitoring.ps1" -ForegroundColor Cyan
Write-Host ""

Write-Host "📚 " -NoNewline -ForegroundColor Blue
Write-Host "Available options:" -ForegroundColor Blue
Write-Host "   -Help          Show detailed help"
Write-Host "   -Status        Check service status"  
Write-Host "   -Stop          Stop all services"
Write-Host "   -Logs          View service logs"
Write-Host "   -Production    Use production configuration"
Write-Host "   -Gpu           Enable GPU monitoring"
Write-Host ""

Write-Host "📖 " -NoNewline -ForegroundColor Blue
Write-Host "Documentation: " -NoNewline -ForegroundColor Blue
Write-Host "docs/MONITORING.md" -ForegroundColor Yellow
Write-Host ""

# Ask if user wants to run the monitoring setup
$response = Read-Host "Would you like to start the monitoring setup now? (y/N)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host ""
    Write-Host "🔧 Starting monitoring setup..." -ForegroundColor Cyan
    & ".\app\integrations\monitoring\run-monitoring.ps1"
} else {
    Write-Host ""
    Write-Host "👍 You can start monitoring later using the commands above." -ForegroundColor Green
    Write-Host ""
}
