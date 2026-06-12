#!/bin/bash
# Quick start script for the SDN Dashboard

echo "=== Starting SDN Load Balancing Dashboard ==="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing Flask dependencies..."
    pip3 install flask flask-cors flask-socketio
fi

# Start the server
echo "Starting web server..."
echo "Dashboard will be available at: http://localhost:5000"
echo ""
python3 app.py

