# CivicPulse AI - Dual Server Startup Script for Windows PowerShell
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Starting CivicPulse AI Platform (Backend + Frontend)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Start Backend
Write-Host "Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python run.py"

Start-Sleep -Seconds 2

# 2. Start Frontend
Write-Host "Starting Vite React Frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "Both servers are launching!" -ForegroundColor Yellow
Write-Host "Backend Swagger API: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "Frontend Portal:     http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Demo Credentials:" -ForegroundColor Cyan
Write-Host "  Citizen:   citizen@example.com / Citizen@12345"
Write-Host "  Admin:     admin@civicpulse.gov.in / Admin@12345"
Write-Host "========================================================" -ForegroundColor Cyan
