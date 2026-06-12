#!/usr/bin/env python3
"""JSON-backed Flask dashboard for SDN load balancing metrics."""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent.parent
LIVE_DIR = BASE_DIR / "data" / "live"
WINDOWS_METRICS_PATH = LIVE_DIR / "windows_live_metrics.json"
LIVE_METRICS_PATH = LIVE_DIR / "live_metrics.json"
CONTROL_PATH = LIVE_DIR / "control.json"

DEFAULT_CONTROL = {
    "routing_mode": "rr",
    "traffic_type": "normal",
    "traffic_running": False,
    "last_command": None,
}

ROUTING_MODES = {"rr", "wrr", "ai"}
TRAFFIC_TYPES = {"normal", "high_load", "burst", "random"}

DEMO_PATHS = [
    ["h1", "e1", "a1", "c1", "a3", "e4", "h8"],
    ["h2", "e1", "a2", "c2", "a4", "e3", "h7"],
    ["h3", "e2", "a1", "c2", "a3", "e4", "h6"],
]

DEMO_LINKS = [
    ("e1-a1", "e1", "a1", 1000),
    ("e1-a2", "e1", "a2", 1000),
    ("a1-c1", "a1", "c1", 1000),
    ("a2-c2", "a2", "c2", 1000),
    ("c1-a3", "c1", "a3", 1000),
    ("c2-a4", "c2", "a4", 1000),
    ("a3-e4", "a3", "e4", 1000),
    ("a4-e3", "a4", "e3", 1000),
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
file_lock = threading.Lock()

app = Flask(__name__, template_folder="templates")


def utc_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically so readers never observe a partially written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def ensure_live_files() -> None:
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    if not CONTROL_PATH.exists():
        write_json(CONTROL_PATH, DEFAULT_CONTROL)
    if not WINDOWS_METRICS_PATH.exists() and not LIVE_METRICS_PATH.exists():
        write_json(
            LIVE_METRICS_PATH,
            {
                "_placeholder": True,
                "message": "Write controller or simulator metrics to this file.",
            },
        )


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
        logger.warning("Ignoring non-object JSON in %s", path)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        logger.warning("Ignoring unreadable metrics file %s: %s", path, error)
    return None


def read_control() -> dict[str, Any]:
    ensure_live_files()
    with file_lock:
        payload = read_json(CONTROL_PATH) or {}
    control = {**DEFAULT_CONTROL, **payload}
    if control["routing_mode"] not in ROUTING_MODES:
        control["routing_mode"] = DEFAULT_CONTROL["routing_mode"]
    if control["traffic_type"] not in TRAFFIC_TYPES:
        control["traffic_type"] = DEFAULT_CONTROL["traffic_type"]
    control["traffic_running"] = bool(control["traffic_running"])
    return control


def update_control(**changes: Any) -> dict[str, Any]:
    with file_lock:
        payload = read_json(CONTROL_PATH) or {}
        control = {**DEFAULT_CONTROL, **payload, **changes}
        write_json(CONTROL_PATH, control)
    return control


def as_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_path(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(node) for node in value]


def normalize_links(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    links = []
    for item in value:
        if not isinstance(item, dict):
            continue
        src = str(item.get("src", "unknown"))
        dst = str(item.get("dst", "unknown"))
        utilization = as_number(
            item.get("utilization_percent", item.get("utilization")), 0.0
        )
        links.append(
            {
                "link_id": str(item.get("link_id", item.get("id", f"{src}-{dst}"))),
                "src": src,
                "dst": dst,
                "capacity_mbps": as_number(item.get("capacity_mbps", item.get("capacity")), 0.0),
                "utilization_percent": utilization,
                "delay_ms": as_number(item.get("delay_ms", item.get("latency_ms")), 0.0),
                "packet_loss_percent": as_number(
                    item.get("packet_loss_percent", item.get("packet_loss")), 0.0
                ),
                "active_flows": as_int(item.get("active_flows"), 0),
                "congested": bool(item.get("congested", utilization >= 80.0)),
            }
        )
    return links


def normalize_flows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    flows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        flows.append(
            {
                "flow_id": str(item.get("flow_id", item.get("id", "unknown"))),
                "src": str(item.get("src", "unknown")),
                "dst": str(item.get("dst", "unknown")),
                "protocol": str(item.get("protocol", "unknown")),
                "bandwidth_mbps": as_number(item.get("bandwidth_mbps"), 0.0),
                "selected_path": as_path(item.get("selected_path")),
                "throughput_mbps": as_number(item.get("throughput_mbps"), 0.0),
                "latency_ms": as_number(item.get("latency_ms"), 0.0),
                "packet_loss_percent": as_number(item.get("packet_loss_percent"), 0.0),
            }
        )
    return flows


def normalize_comparison(value: Any) -> dict[str, dict[str, float]]:
    defaults = {
        "rr": {"throughput_mbps": 980, "latency_ms": 45, "packet_loss_percent": 0.5, "jitter_ms": 12},
        "wrr": {"throughput_mbps": 1085, "latency_ms": 32, "packet_loss_percent": 0.3, "jitter_ms": 8},
        "ai": {"throughput_mbps": 1250, "latency_ms": 25, "packet_loss_percent": 0.1, "jitter_ms": 4},
    }
    if not isinstance(value, dict):
        return defaults
    comparison: dict[str, dict[str, float]] = {}
    for mode, mode_defaults in defaults.items():
        metrics = value.get(mode)
        if not isinstance(metrics, dict):
            metrics = {}
        comparison[mode] = {
            key: as_number(metrics.get(key), default) for key, default in mode_defaults.items()
        }
    return comparison


def normalize_metrics(
    payload: dict[str, Any],
    control: dict[str, Any],
    source_file: Path,
) -> dict[str, Any]:
    links = normalize_links(payload.get("links"))
    flows = normalize_flows(payload.get("flows"))
    dqn_payload = payload.get("dqn")
    if not isinstance(dqn_payload, dict):
        dqn_payload = {}
    congested_links = sum(1 for link in links if link["congested"])

    return {
        "timestamp": str(payload.get("timestamp", utc_timestamp())),
        "running_mode": str(payload.get("running_mode", "external_metrics")),
        "routing_mode": control["routing_mode"],
        "traffic_type": control["traffic_type"],
        "traffic_running": control["traffic_running"],
        "last_command": control.get("last_command"),
        "active_flows": as_int(payload.get("active_flows"), len(flows)),
        "total_throughput_mbps": as_number(
            payload.get("total_throughput_mbps", payload.get("throughput")), 0.0
        ),
        "average_latency_ms": as_number(
            payload.get("average_latency_ms", payload.get("latency")), 0.0
        ),
        "packet_loss_percent": as_number(
            payload.get("packet_loss_percent", payload.get("packet_loss")), 0.0
        ),
        "jitter_ms": as_number(payload.get("jitter_ms"), 0.0),
        "congested_links": as_int(payload.get("congested_links"), congested_links),
        "selected_path": as_path(payload.get("selected_path")),
        "selected_link": str(payload.get("selected_link", dqn_payload.get("chosen_link", "N/A"))),
        "path_score": as_number(payload.get("path_score"), 0.0),
        "dqn": {
            "episode": as_int(dqn_payload.get("episode"), 0),
            "reward": as_number(dqn_payload.get("reward"), 0.0),
            "epsilon": as_number(dqn_payload.get("epsilon"), 0.0),
            "chosen_link": str(dqn_payload.get("chosen_link", payload.get("selected_link", "N/A"))),
        },
        "comparison": normalize_comparison(payload.get("comparison")),
        "links": links,
        "flows": flows,
        "data_source": "live_metrics_file",
        "metrics_file": source_file.name,
    }


def demo_traffic_range(control: dict[str, Any]) -> tuple[float, float, tuple[int, int]]:
    if not control["traffic_running"]:
        return 100, 320, (0, 4)
    traffic_type = control["traffic_type"]
    if traffic_type == "high_load":
        return 800, 1200, (12, 20)
    if traffic_type == "burst":
        return (850, 1200, (10, 20)) if random.random() > 0.45 else (180, 520, (3, 10))
    if traffic_type == "random":
        return 100, 1200, (0, 20)
    return 320, 820, (4, 13)


def generate_demo_metrics(control: dict[str, Any] | None = None) -> dict[str, Any]:
    control = control or read_control()
    low, high, flow_range = demo_traffic_range(control)
    throughput = round(random.uniform(low, high), 1)
    active_flows = random.randint(*flow_range)
    latency = round(random.uniform(5, 60), 1)
    packet_loss = round(random.uniform(0, 5), 2)
    selected_path = random.choice(DEMO_PATHS)
    selected_link = "-".join(selected_path[1:3])
    links = []
    for link_id, src, dst, capacity in DEMO_LINKS:
        utilization = round(random.uniform(18, 98), 1)
        links.append(
            {
                "link_id": link_id,
                "src": src,
                "dst": dst,
                "capacity_mbps": capacity,
                "utilization_percent": utilization,
                "delay_ms": round(random.uniform(1.2, 14), 1),
                "packet_loss_percent": round(random.uniform(0, 4.5), 2),
                "active_flows": random.randint(0, max(1, min(active_flows, 8))),
                "congested": utilization >= 80,
            }
        )
    flows = []
    for index in range(active_flows):
        path = random.choice(DEMO_PATHS)
        bandwidth = round(random.uniform(4, 80), 1)
        flows.append(
            {
                "flow_id": f"flow_{index + 1:03d}",
                "src": path[0],
                "dst": path[-1],
                "protocol": random.choice(["TCP", "UDP"]),
                "bandwidth_mbps": bandwidth,
                "selected_path": path,
                "throughput_mbps": round(bandwidth * random.uniform(0.78, 0.99), 1),
                "latency_ms": round(random.uniform(5, 60), 1),
                "packet_loss_percent": round(random.uniform(0, 5), 2),
            }
        )

    return {
        "timestamp": utc_timestamp(),
        "running_mode": "demo",
        "routing_mode": control["routing_mode"],
        "traffic_type": control["traffic_type"],
        "traffic_running": control["traffic_running"],
        "last_command": control.get("last_command"),
        "active_flows": active_flows,
        "total_throughput_mbps": throughput,
        "average_latency_ms": latency,
        "packet_loss_percent": packet_loss,
        "jitter_ms": round(random.uniform(1, 15), 1),
        "congested_links": sum(1 for link in links if link["congested"]),
        "selected_path": selected_path,
        "selected_link": selected_link,
        "path_score": round(random.uniform(0.72, 0.99), 2),
        "dqn": {
            "episode": 1482 + int(time.time()) % 500,
            "reward": round(random.uniform(0.82, 0.99), 3),
            "epsilon": 0.05,
            "chosen_link": selected_link,
        },
        "comparison": normalize_comparison(None),
        "links": links,
        "flows": flows,
        "data_source": "demo_fallback",
    }


def current_metrics() -> dict[str, Any]:
    ensure_live_files()
    control = read_control()
    for path in (WINDOWS_METRICS_PATH, LIVE_METRICS_PATH):
        payload = read_json(path)
        if payload and not payload.get("_placeholder"):
            return normalize_metrics(payload, control, path)
    return generate_demo_metrics(control)


@app.after_request
def disable_api_cache(response):
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/metrics")
def metrics():
    return jsonify(current_metrics())


@app.route("/api/status")
def status():
    control = read_control()
    metrics_payload = current_metrics()
    return jsonify(
        {
            **control,
            "running_mode": metrics_payload["running_mode"],
            "data_source": metrics_payload["data_source"],
            "metrics_file": metrics_payload.get("metrics_file"),
            "timestamp": metrics_payload["timestamp"],
        }
    )


@app.route("/api/topology")
def topology():
    metrics_payload = current_metrics()
    return jsonify(
        {
            "selected_path": metrics_payload["selected_path"],
            "selected_link": metrics_payload["selected_link"],
            "path_score": metrics_payload["path_score"],
            "links": metrics_payload["links"],
            "data_source": metrics_payload["data_source"],
        }
    )


@app.route("/api/demo_metrics")
def demo_metrics():
    return jsonify(generate_demo_metrics())


@app.route("/api/set_mode", methods=["GET", "POST"])
def set_mode():
    mode = request.args.get("mode", "").lower()
    if mode not in ROUTING_MODES:
        return jsonify({"error": "mode must be one of: rr, wrr, ai"}), 400
    control = update_control(routing_mode=mode, last_command=f"set_mode:{mode}")
    return jsonify({"status": "ok", **control})


@app.route("/api/start_traffic", methods=["GET", "POST"])
def start_traffic():
    traffic_type = request.args.get("type", "").lower()
    if traffic_type not in TRAFFIC_TYPES:
        return jsonify({"error": "type must be one of: normal, high_load, burst, random"}), 400
    control = update_control(
        traffic_type=traffic_type,
        traffic_running=True,
        last_command=f"start_traffic:{traffic_type}",
    )
    return jsonify({"status": "ok", **control})


@app.route("/api/stop_traffic", methods=["GET", "POST"])
def stop_traffic():
    control = update_control(traffic_running=False, last_command="stop_traffic")
    return jsonify({"status": "ok", **control})


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "timestamp": utc_timestamp()})


ensure_live_files()

if __name__ == "__main__":
    print("AI-Powered SDN Load Balancing Dashboard")
    print("Open http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
