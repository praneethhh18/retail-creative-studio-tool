<# 
.SYNOPSIS
    Development helper script for Windows PowerShell

.DESCRIPTION
    Provides commands for setting up and running the Retail Creative Tool

.EXAMPLE
    .\dev.ps1 install
    .\dev.ps1 backend
    .\dev.ps1 frontend
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("install-backend", "install-frontend", "install", "backend", "frontend", "test", "lint", "docker-up", "docker-down", "help")]
    [string]$Command = "help"
)

function Write-Status {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[x] $Message" -ForegroundColor Red
}

function Install-Backend {
    Write-Status "Installing backend dependencies..."
    Push-Location backend
    
    if (-not (Test-Path "venv")) {
        python -m venv venv
    }
    
    & .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    pip install pytest pytest-cov black flake8 mypy
    
    Pop-Location
    Write-Status "Backend dependencies installed!"
}

function Install-Frontend {
    Write-Status "Installing frontend dependencies..."
    Push-Location frontend
    npm install
    npx playwright install chromium
    Pop-Location
    Write-Status "Frontend dependencies installed!"
}

function Start-Backend {
    Write-Status "Starting backend server..."
    Push-Location backend
    & .\venv\Scripts\Activate.ps1
    uvicorn app.main:app --reload --port 8000
    Pop-Location
}

function Start-Frontend {
    Write-Status "Starting frontend dev server..."
    Push-Location frontend
    npm run dev
    Pop-Location
}

function Invoke-Tests {
    Write-Status "Running all tests..."
    
    Write-Status "Backend tests..."
    Push-Location backend
    & .\venv\Scripts\Activate.ps1
    pytest tests/ -v --cov=app
    Pop-Location
    
    Write-Status "Frontend tests..."
    Push-Location frontend
    npm run test:unit
    Pop-Location
    
    Write-Status "All tests completed!"
}

function Invoke-Lint {
    Write-Status "Linting code..."
    
    Write-Status "Backend linting..."
    Push-Location backend
    & .\venv\Scripts\Activate.ps1
    black app --check
    flake8 app --max-line-length=120
    Pop-Location
    
    Write-Status "Frontend linting..."
    Push-Location frontend
    npm run lint
    Pop-Location
    
    Write-Status "Linting completed!"
}

function Start-Docker {
    Write-Status "Building and starting Docker containers..."
    docker-compose up --build
}

function Stop-Docker {
    Write-Status "Stopping Docker containers..."
    docker-compose down
}

function Show-Help {
    Write-Host @"
Retail Creative Tool - Development Helper

Usage: .\dev.ps1 [command]

Commands:
  install-backend   Install Python dependencies
  install-frontend  Install Node.js dependencies
  install           Install all dependencies
  backend           Start backend development server
  frontend          Start frontend development server
  test              Run all tests
  lint              Lint all code
  docker-up         Build and start Docker containers
  docker-down       Stop Docker containers
  help              Show this help message
"@
}

# Main
switch ($Command) {
    "install-backend" { Install-Backend }
    "install-frontend" { Install-Frontend }
    "install" { 
        Install-Backend
        Install-Frontend
    }
    "backend" { Start-Backend }
    "frontend" { Start-Frontend }
    "test" { Invoke-Tests }
    "lint" { Invoke-Lint }
    "docker-up" { Start-Docker }
    "docker-down" { Stop-Docker }
    "help" { Show-Help }
    default { Show-Help }
}
