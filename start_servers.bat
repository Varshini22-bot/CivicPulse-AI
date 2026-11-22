@echo off
echo ========================================================
echo   Starting CivicPulse AI Platform (Backend + Frontend)
echo ========================================================
echo.
echo 1. Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "CivicPulse AI - Backend" cmd /k "cd backend && python run.py"

timeout /t 2 /nobreak >nul

echo 2. Starting Vite React Frontend on http://localhost:5173 ...
start "CivicPulse AI - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are launching!
echo Backend Swagger API: http://127.0.0.1:8000/docs
echo Frontend Portal:     http://localhost:5173
echo.
echo Demo Accounts:
echo - Citizen:   citizen@example.com / Citizen@12345
echo - Admin:     admin@civicpulse.gov.in / Admin@12345
echo ========================================================
pause
