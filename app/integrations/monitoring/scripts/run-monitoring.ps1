# =============================================================================
# vLLM FastAPI Monitoring Runner Script
# =============================================================================
# This is a convenience script to run monitoring from the app/integrations/monitoring directory
# It changes to the docker directory and runs the setup script

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

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DockerDir = Join-Path $ScriptDir "docker"
$SetupScript = Join-Path $ScriptDir "scripts\setup-monitoring.ps1"

# Check if we're in the right directory structure
if (-not (Test-Path $DockerDir)) {
    Write-Host "❌ Docker directory not found. Please run this script from app/integrations/monitoring/" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $SetupScript)) {
    Write-Host "❌ Setup script not found at $SetupScript" -ForegroundColor Red
    exit 1
}

# Change to docker directory
Push-Location $DockerDir

try {
    # Build arguments for the setup script
    $setupArgs = @()
    
    if ($Help) { $setupArgs += "-Help" }
    if ($Gpu) { $setupArgs += "-Gpu" }
    if ($Production) { $setupArgs += "-Production" }
    if ($NoAlerting) { $setupArgs += "-NoAlerting" }
    if ($User) { $setupArgs += "-User", $User }
    if ($Password) { $setupArgs += "-Password", $Password }
    if ($Status) { $setupArgs += "-Status" }
    if ($Stop) { $setupArgs += "-Stop" }
    if ($Logs) { $setupArgs += "-Logs" }
    
    # Run the setup script
    & $SetupScript @setupArgs
}
finally {
    # Always return to original directory
    Pop-Location
}
