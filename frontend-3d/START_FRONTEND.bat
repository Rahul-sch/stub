@echo off
echo ========================================
echo Rig Alpha - Starting 3D Frontend
echo ========================================
echo.

REM Check if node_modules exists
if not exist "node_modules\" (
    echo Dependencies not installed. Running npm install...
    echo.
    call npm install --legacy-peer-deps
    echo.
)

echo Starting Vite dev server...
echo Frontend will be available at: http://localhost:3000
echo.
echo Controls:
echo   WASD - Move
echo   Mouse - Look around
echo   Space - Jump
echo   Shift - Sprint
echo   ESC - Release cursor
echo.
call npm run dev

pause
