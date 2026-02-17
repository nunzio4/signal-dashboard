@echo off
echo ============================================
echo   Signal Dashboard - Starting...
echo ============================================
echo.

:: Start backend
echo [1/2] Starting FastAPI backend on port 8000...
start "Signal Dashboard - Backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak > NUL

:: Start frontend
echo [2/2] Starting React frontend on port 5173...
start "Signal Dashboard - Frontend" cmd /k "cd /d "%~dp0frontend" && "C:\Program Files\nodejs\npx.cmd" vite --host 127.0.0.1 --port 5173"

:: Wait for frontend
timeout /t 3 /nobreak > NUL

echo.
echo ============================================
echo   Dashboard is ready!
echo   Open: http://localhost:5173
echo ============================================
echo.
echo Press any key to open in browser...
pause > NUL
start http://localhost:5173
