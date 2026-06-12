# AI-Powered SDN Load Balancing Dashboard

This dashboard serves the uploaded Tailwind frontend from Flask and refreshes SDN metrics once per second. The dashboard does not start Mininet, Ryu, Open vSwitch, or a Windows simulator. Those processes remain separate and communicate with the page through JSON files.

## Dashboard Files

- Flask backend: `dashboard/app.py`
- Frontend template: `dashboard/templates/index.html`
- Shared control file: `data/live/control.json`
- Windows simulator metrics: `data/live/windows_live_metrics.json`
- Linux controller metrics: `data/live/live_metrics.json`

The backend checks metrics sources in this order:

1. `data/live/windows_live_metrics.json`
2. `data/live/live_metrics.json`
3. Changing Flask-generated demo metrics

The initial `live_metrics.json` is a placeholder. Until a simulator or controller replaces it with metrics, the API returns changing fallback data with `"data_source": "demo_fallback"`. File-backed metrics return `"data_source": "live_metrics_file"`.

## Run On Windows

From the repository root:

```bat
python dashboard\app.py
```

Or use the launcher:

```bat
scripts\run_dashboard_windows.bat
```

Open `http://127.0.0.1:5000`.

## Run On Ubuntu Or Linux

From the repository root:

```bash
python3 dashboard/app.py
```

Or use the launcher:

```bash
chmod +x scripts/run_dashboard_linux.sh
./scripts/run_dashboard_linux.sh
```

Open `http://127.0.0.1:5000`.

## API Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/metrics` | Normalized live metrics or labeled fallback data |
| `GET /api/status` | Current control state and active metrics source |
| `GET /api/topology` | Selected path and normalized link details |
| `GET /api/demo_metrics` | Explicitly request generated demo data |
| `GET /api/set_mode?mode=rr` | Select Round Robin routing |
| `GET /api/set_mode?mode=wrr` | Select Weighted Round Robin routing |
| `GET /api/set_mode?mode=ai` | Select AI/DQN routing |
| `GET /api/start_traffic?type=normal` | Start normal traffic |
| `GET /api/start_traffic?type=high_load` | Start high-load traffic |
| `GET /api/start_traffic?type=burst` | Start burst traffic |
| `GET /api/start_traffic?type=random` | Start randomized traffic |
| `GET /api/stop_traffic` | Stop traffic generation |
| `GET /api/health` | Basic Flask health check |

The command endpoints update `data/live/control.json`. A simulator or controller can watch that file and act on routing and traffic commands.

## Test With Browser Or Curl

```bash
curl http://127.0.0.1:5000/api/metrics
curl http://127.0.0.1:5000/api/status
curl "http://127.0.0.1:5000/api/set_mode?mode=ai"
curl "http://127.0.0.1:5000/api/start_traffic?type=high_load"
curl http://127.0.0.1:5000/api/stop_traffic
```

The dashboard page polls `/api/metrics` every second. Overview cards, DQN status, selected path, comparison values, link rows, flow rows, status labels, and SVG history charts update without a page refresh.

## Connect A Windows Simulator

Write a JSON object to:

```text
data/live/windows_live_metrics.json
```

The dashboard prefers this file when both Windows and Linux metrics files exist. Write UTF-8 JSON and replace the file atomically when possible so Flask never reads a partially written update.

## Connect Linux Ryu Or Mininet Mode

Write a JSON object to:

```text
data/live/live_metrics.json
```

Replace the placeholder object with controller metrics. Linux mode remains separate from the dashboard process.

## Metrics Shape

The dashboard accepts partial JSON safely. Missing values receive defaults. For the richest display, provide:

```json
{
  "timestamp": "2026-05-31T12:00:00",
  "running_mode": "windows_native",
  "total_throughput_mbps": 52.4,
  "average_latency_ms": 12.8,
  "packet_loss_percent": 1.7,
  "selected_path": ["h1", "e1", "a1", "c1", "a3", "e4", "h8"],
  "dqn": {
    "episode": 1482,
    "reward": 0.987,
    "epsilon": 0.05,
    "chosen_link": "e1-a1"
  },
  "comparison": {
    "rr": {"throughput_mbps": 980, "latency_ms": 45, "packet_loss_percent": 0.5, "jitter_ms": 12},
    "wrr": {"throughput_mbps": 1085, "latency_ms": 32, "packet_loss_percent": 0.3, "jitter_ms": 8},
    "ai": {"throughput_mbps": 1250, "latency_ms": 25, "packet_loss_percent": 0.1, "jitter_ms": 4}
  },
  "links": [],
  "flows": []
}
```

## Limitations

- Demo metrics are presentation fallback data only. The page labels them as `demo_fallback`.
- Control endpoints persist commands, but an external simulator or controller must watch `control.json` to perform real network actions.
- The topology image, Tailwind runtime, Google font, and Material icons use remote URLs. Core metric updates still work if those assets are unavailable.
