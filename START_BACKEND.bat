@echo off
echo ========================================
echo Rig Alpha - Starting Flask Backend
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if Flask-SocketIO is installed
python -c "import flask_socketio" 2>nul

if %errorlevel% neq 0 (
    echo Flask-SocketIO not installed. Installing now...
    pip install flask-socketio==5.3.6 python-socketio==5.10.0 python-engineio==4.8.0
    echo.
)

echo Starting Flask dashboard with SocketIO...
echo Backend will be available at: http://localhost:5000
echo WebSocket endpoint: ws://localhost:5000/socket.io
echo.
python dashboard.py

pause
