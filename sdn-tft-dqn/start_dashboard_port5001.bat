@echo off
REM Start dashboard on port 5001 (if 5000 is in use)

echo ========================================
echo Starting SDN Load Balancing Dashboard
echo Using Port 5001
echo ========================================
echo.

REM Set port environment variable
set PORT=5001

REM Start the server
python app.py

pause

