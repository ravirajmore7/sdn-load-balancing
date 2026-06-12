@echo off
REM Quick start script for the SDN Dashboard on Windows

echo ========================================
echo Starting SDN Load Balancing Dashboard
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Installing Flask dependencies...
    pip install flask flask-cors flask-socketio gevent gevent-websocket
)

REM Create necessary directories
if not exist "data\raw" mkdir data\raw
if not exist "data\processed" mkdir data\processed
if not exist "data\predictions" mkdir data\predictions
if not exist "models" mkdir models
if not exist "static" mkdir static
if not exist "experiments" mkdir experiments

REM Start the server
echo.
echo Starting web server...
echo Dashboard will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python app.py

pause

