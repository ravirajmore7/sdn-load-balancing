# 🚀 Quick Start Guide - SDN Dashboard

## Step 1: Install Dependencies

```bash
cd sdn-tft-dqn
pip install -r requirements.txt
```

## Step 2: Start the Server

```bash
python app.py
```

You should see:
```
============================================================
AI-Powered SDN Load Balancing Dashboard
============================================================
Loading models...
✓ Dashboard available at: http://localhost:5000
```

## Step 3: Open Your Browser

Open: **http://localhost:5000**

## Step 4: Test the Server (Optional)

In another terminal:
```bash
python test_server.py
```

## 🎯 What You'll See

The dashboard works in **demo mode** by default, showing sample data. It will automatically use real data when you:

1. Run the preprocessing script: `python utils/preprocessing.py`
2. Train the TFT model: `python models/tft_model.py`
3. Train the DQN agent: `python models/dqn_agent.py`

## 📊 Dashboard Pages

- **Overview** (`/`) - Main dashboard with metrics
- **Traffic Forecast** (`/traffic-forecast`) - TFT predictions
- **Load Balancing** (`/load-balancing`) - DQN agent status
- **Performance Comparison** (`/performance-comparison`) - Algorithm comparison

## 🔧 Troubleshooting

### Port 5000 already in use?
Change the port in `app.py`:
```python
socketio.run(app, host='0.0.0.0', port=8080, ...)
```

### Import errors?
The dashboard works without models! It will run in demo mode.

### WebSocket not working?
Make sure Flask-SocketIO is installed:
```bash
pip install flask-socketio
```

## ✅ Features

- ✅ Works without trained models (demo mode)
- ✅ Real-time WebSocket updates
- ✅ Responsive design
- ✅ Error handling
- ✅ Sample data generation
- ✅ Health check endpoint

## 🎉 You're Ready!

The dashboard is fully functional and ready to use!

