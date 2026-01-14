# Quick Start Script for Sensor Data Pipeline
# This script starts Docker containers using the full Docker path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Sensor Data Pipeline - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Define Docker path
$dockerPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$dockerComposePath = "C:\Program Files\Docker\Docker\resources\bin\docker-compose.exe"

# Check if docker-compose exists, otherwise use 'docker compose'
if (Test-Path $dockerComposePath) {
    $composeCommand = "& `"$dockerComposePath`" up -d"
} else {
    $composeCommand = "& `"$dockerPath`" compose up -d"
}

Write-Host "Step 1: Starting Docker containers..." -ForegroundColor Yellow
Invoke-Expression $composeCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Containers started successfully!" -ForegroundColor Green
    Write-Host ""

    Write-Host "Step 2: Waiting 60 seconds for Kafka to initialize..." -ForegroundColor Yellow
    Write-Host "(Kafka needs time to start up properly)" -ForegroundColor Gray
    Start-Sleep -Seconds 60

    Write-Host "✓ Initialization wait complete!" -ForegroundColor Green
    Write-Host ""

    Write-Host "Step 3: Checking container status..." -ForegroundColor Yellow
    if (Test-Path $dockerComposePath) {
        & "$dockerComposePath" ps
    } else {
        & "$dockerPath" compose ps
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Docker containers are ready!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Open a NEW PowerShell window and run:" -ForegroundColor White
    Write-Host "   cd c:\Users\rahul\Desktop\stubby\stub" -ForegroundColor Gray
    Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "   python consumer.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Open ANOTHER PowerShell window and run:" -ForegroundColor White
    Write-Host "   cd c:\Users\rahul\Desktop\stubby\stub" -ForegroundColor Gray
    Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "   python producer.py" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "✗ Failed to start containers" -ForegroundColor Red
    Write-Host "Check if Docker Desktop is running" -ForegroundColor Yellow
}
