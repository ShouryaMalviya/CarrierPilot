# ==============================================================================
# CareerPilot AI — Local Development Environment Startup Script (PowerShell)
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " CareerPilot AI — Launching Local Development Services    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python Virtualenv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtualenv not found. Please create one with 'python -m venv .venv'" -ForegroundColor Red
    exit 1
}

# 2. Seed Demo Environment
Write-Host "`n[1/3] Ensuring Database Migrations and Demo Benchmark State..." -ForegroundColor Yellow
& .venv\Scripts\python.exe scripts\seed_demo_environment.py

# 3. Start Backend in Background or Tab
Write-Host "`n[2/3] Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$BackendProcess = Start-Process -FilePath ".venv\Scripts\uvicorn.exe" -ArgumentList "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload" -WorkingDirectory "backend" -PassThru

# 4. Start Frontend
Write-Host "`n[3/3] Launching Vite Frontend on http://localhost:5173..." -ForegroundColor Green
Write-Host "Press Ctrl+C to terminate services." -ForegroundColor White

npm --prefix frontend run dev

