# SDN Load Balancing Dashboard

A modern web-based dashboard for visualizing and monitoring AI-powered SDN load balancing.

## Features

- **Real-time Metrics**: Live network throughput, latency, and packet loss monitoring
- **Traffic Forecast**: TFT-based traffic prediction visualization
- **Load Balancing**: Real-time DQN agent status and traffic distribution
- **Performance Comparison**: Side-by-side comparison of RR, WRR, and DQN algorithms

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Web Server

```bash
python app.py
```

The dashboard will be available at: `http://localhost:5000`

### 3. Access the Dashboards

- **Overview**: `http://localhost:5000/`
- **Traffic Forecast**: `http://localhost:5000/traffic-forecast`
- **Load Balancing**: `http://localhost:5000/load-balancing`
- **Performance Comparison**: `http://localhost:5000/performance-comparison`

## API Endpoints

### Metrics
- `GET /api/metrics` - Get current network metrics
- `GET /api/forecast` - Get traffic forecast data
- `GET /api/load-balancing/status` - Get DQN agent status
- `GET /api/load-balancing/traffic-distribution` - Get traffic distribution
- `GET /api/load-balancing/link-utilization` - Get per-link utilization
- `GET /api/comparison` - Get performance comparison data

### Simulation Control
- `POST /api/simulation/start` - Start network simulation
- `POST /api/simulation/stop` - Stop network simulation

## WebSocket Events

The dashboard uses WebSocket for real-time updates:

- `metrics_update` - Emitted when metrics are updated
- `connect` - Client connection event
- `disconnect` - Client disconnection event

## Architecture

```
app.py                 # Flask web server
├── templates/         # HTML templates
│   ├── overview.html
│   ├── traffic_forecast.html
│   ├── load_balancing.html
│   └── performance_comparison.html
└── static/           # Static assets (CSS, JS, images)
```

## Data Flow

1. **Backend Models** → Load TFT and DQN models on startup
2. **API Endpoints** → Serve data from processed CSV files and models
3. **WebSocket** → Push real-time updates to connected clients
4. **Frontend** → Fetch data via AJAX and WebSocket, render visualizations

## Customization

### Adding New Metrics

1. Update `app.py` to add new API endpoint
2. Modify corresponding HTML template to display the metric
3. Add JavaScript to fetch and render the data

### Styling

The dashboard uses Tailwind CSS. Modify the HTML templates to change styling.

### Data Sources

- Metrics: `data/processed/processed.csv`
- Forecasts: `data/predictions/tft_forecast.csv`
- Comparison: `experiments/results.csv`
- Models: `models/dqn_best.pth`, `models/tft.ckpt`

## Troubleshooting

### Dashboard not loading
- Check if Flask server is running: `python app.py`
- Verify port 5000 is not in use
- Check browser console for errors

### No data displayed
- Ensure data files exist in `data/processed/` and `data/predictions/`
- Run preprocessing and training scripts first
- Check API endpoints return data: `curl http://localhost:5000/api/metrics`

### WebSocket connection issues
- Ensure Flask-SocketIO is installed: `pip install flask-socketio`
- Check firewall settings
- Verify server logs for connection errors

## Development

### Running in Debug Mode

```bash
export FLASK_ENV=development
python app.py
```

### Adding New Pages

1. Create HTML template in `templates/`
2. Add route in `app.py`
3. Update navigation in all templates

## License

[Add your license information]

