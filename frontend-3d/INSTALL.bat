@echo off
REM Quick install script for Rig Alpha 3D Digital Twin

echo ========================================
echo Rig Alpha 3D Digital Twin - Installer
echo ========================================
echo.

echo [1/3] Installing frontend dependencies...
call npm install --legacy-peer-deps

if %errorlevel% neq 0 (
    echo.
    echo ERROR: npm install failed
    echo Try running: npm install --legacy-peer-deps --force
    pause
    exit /b 1
)

echo.
echo [2/3] Checking backend dependencies...
cd ..\
python -c "import flask_socketio" 2>nul

if %errorlevel% neq 0 (
    echo Flask-SocketIO not found. Installing...
    pip install flask-socketio==5.3.6 python-socketio==5.10.0 python-engineio==4.8.0
) else (
    echo Flask-SocketIO already installed.
)

echo.
echo [3/3] Installation complete!
echo.
echo ========================================
echo Next steps:
echo ========================================
echo 1. Start backend: python dashboard.py
echo 2. Start frontend: npm run dev
echo 3. Open browser: http://localhost:3000
echo ========================================
pause
