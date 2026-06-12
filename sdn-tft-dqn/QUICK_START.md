# Quick Start Guide

## Running the SDN Load Balancing Dashboard

### Windows

1. **Double-click** `start_dashboard.bat` OR

2. **Run from command line:**
   ```powershell
   cd sdn-tft-dqn
   python app.py
   ```

3. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

### Linux/Mac

1. **Run the shell script:**
   ```bash
   cd sdn-tft-dqn
   chmod +x start_dashboard.sh
   ./start_dashboard.sh
   ```

2. **Or run directly:**
   ```bash
   cd sdn-tft-dqn
   python3 app.py
   ```

3. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

## Prerequisites

Make sure you have Python 3.8+ installed. The app will automatically install required dependencies if missing:
- Flask
- Flask-CORS
- Flask-SocketIO
- Gevent
- NumPy
- Pandas

## Troubleshooting

### Port Already in Use
If port 5000 is already in use, you can change it in `app.py`:
```python
socketio.run(app, host='0.0.0.0', port=5001, ...)
```

### Import Errors
If you see import errors, install dependencies manually:
```bash
pip install -r requirements.txt
```

### Directory Errors
The app automatically creates necessary directories. If you see errors, ensure you have write permissions.

## Features

- **Overview Dashboard**: Real-time network metrics
- **Traffic Forecast**: TFT model predictions
- **Load Balancing**: DQN agent routing decisions
- **Performance Comparison**: Algorithm comparison charts

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

