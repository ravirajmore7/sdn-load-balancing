#!/usr/bin/env python3
"""
Flask Web Server for SDN Load Balancing Dashboard
Serves the frontend and provides API endpoints for real-time data
"""

import os
import sys
import json
import time
import logging
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Import configuration
try:
    from config import SERVERS, NETWORK_LINKS, SIMULATION_CONFIG, DATA_PATHS
except ImportError:
    # Fallback if config.py is not found (e.g. running from different dir)
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import SERVERS, NETWORK_LINKS, SIMULATION_CONFIG, DATA_PATHS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import backend modules
try:
    from models.dqn_agent import DQNAgent
    from gym_env.sdn_env import SDNEnv
    MODELS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import models ({e}). Running in demo mode.")
    MODELS_AVAILABLE = False
    DQNAgent = None
    SDNEnv = None

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

class SimulationManager:
    """Manages the network simulation state and logic"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.current_metrics = {
            'throughput': SIMULATION_CONFIG['base_throughput'],
            'latency': SIMULATION_CONFIG['base_latency'],
            'packet_loss': SIMULATION_CONFIG['base_packet_loss'],
            'timestamp': datetime.now().isoformat()
        }
        self.load_balancing_state = {
            'current_link': None,
            'previous_link': None,
            'link_loads': {},
            'link_utilizations': {},
            'notifications': []
        }
        self.dqn_agent = None
        self.sdn_env = None
        self.load_models()

    def load_models(self):
        """Load trained models"""
        if not MODELS_AVAILABLE:
            logger.info("Models not available - running in demo mode")
            return

        try:
            if os.path.exists(DATA_PATHS['processed_csv']):
                try:
                    self.sdn_env = SDNEnv(
                        data_csv=DATA_PATHS['processed_csv'], 
                        forecast_csv=DATA_PATHS['forecast_csv'], 
                        n_links=16
                    )
                    
                    if os.path.exists(DATA_PATHS['dqn_model']):
                        state_dim = self.sdn_env.observation_space.shape[0]
                        action_dim = self.sdn_env.action_space.n
                        self.dqn_agent = DQNAgent(state_dim=state_dim, action_dim=action_dim)
                        self.dqn_agent.load(DATA_PATHS['dqn_model'])
                        self.dqn_agent.epsilon = 0.0  # Disable exploration
                        logger.info("DQN model loaded successfully")
                    else:
                        logger.info("DQN model not found, using default agent")
                except Exception as e:
                    logger.error(f"Error initializing environment: {e}")
            else:
                logger.info("Processed data not found - using sample data")
        except Exception as e:
            logger.error(f"Error loading models: {e}")

    def start(self):
        """Start the simulation thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Simulation started")
            return True
        return False

    def stop(self):
        """Stop the simulation thread"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1.0)
            logger.info("Simulation stopped")
            return True
        return False

    def _run_loop(self):
        """Main simulation loop"""
        base_throughput = SIMULATION_CONFIG['base_throughput']
        base_latency = SIMULATION_CONFIG['base_latency']
        base_packet_loss = SIMULATION_CONFIG['base_packet_loss']
        
        previous_throughput = base_throughput
        previous_latency = base_latency

        while self.running:
            try:
                # Simulate network conditions
                network_factor = np.random.uniform(0.8, 1.2)
                
                self.current_metrics['throughput'] = round(
                    base_throughput * network_factor + np.random.uniform(-0.2, 0.3), 2
                )
                self.current_metrics['latency'] = round(
                    base_latency / network_factor + np.random.uniform(-2, 3), 1
                )
                self.current_metrics['packet_loss'] = round(
                    max(0.01, base_packet_loss + np.random.uniform(-0.02, 0.05)), 3
                )
                self.current_metrics['timestamp'] = datetime.now().isoformat()
                
                # Check for significant changes
                throughput_change = abs(self.current_metrics['throughput'] - previous_throughput) / previous_throughput
                latency_change = abs(self.current_metrics['latency'] - previous_latency) / previous_latency if previous_latency > 0 else 0
                
                if throughput_change > 0.15 or latency_change > 0.2:
                    self.add_notification(
                        'network_change',
                        f'🌐 Network conditions changed: Throughput {self.current_metrics["throughput"]:.2f} Tbps, Latency {self.current_metrics["latency"]:.1f}ms',
                        {
                            'throughput': self.current_metrics['throughput'],
                            'latency': self.current_metrics['latency'],
                            'packet_loss': self.current_metrics['packet_loss']
                        }
                    )
                
                previous_throughput = self.current_metrics['throughput']
                previous_latency = self.current_metrics['latency']
                
                socketio.emit('metrics_update', self.current_metrics)
                time.sleep(SIMULATION_CONFIG['update_interval'])
                
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(SIMULATION_CONFIG['update_interval'])

    def add_notification(self, type, message, data=None):
        """Add a notification and emit it"""
        notification = {
            'type': type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': data or {}
        }
        
        self.load_balancing_state['notifications'].append(notification)
        if len(self.load_balancing_state['notifications']) > 50:
            self.load_balancing_state['notifications'].pop(0)
        
        socketio.emit('load_balancing_notification', notification)
        logger.info(f"Notification: {message}")

# Initialize Simulation Manager
sim_manager = SimulationManager()

# Helper functions
def generate_dynamic_loads():
    """Generate dynamic loads for all servers"""
    loads = {}
    for server in SERVERS:
        base = server['base_load']
        variance = server['load_variance']
        load = base + np.random.uniform(-variance, variance)
        load = max(0.1, min(0.99, load))
        loads[server['id']] = load
    return loads

def calculate_link_traffic(link, server_loads):
    """Calculate traffic on a link based on server loads"""
    server1_load = server_loads.get(link['servers'][0], 0.5)
    server2_load = server_loads.get(link['servers'][1], 0.5)
    avg_load = (server1_load + server2_load) / 2
    traffic = link['capacity'] * avg_load * (0.8 + np.random.uniform(0, 0.4))
    return round(traffic, 2)

def generate_sample_forecast_data(data_type='actual'):
    """Generate sample forecast data"""
    base = 1.0
    np.random.seed(42)
    if data_type == 'actual':
        data = [float(max(0.1, base + np.sin(i/10) * 0.3 + np.random.normal(0, 0.1))) for i in range(36)]
    else:
        data = [float(max(0.1, base + np.sin(i/10) * 0.3 + np.random.normal(0, 0.05))) for i in range(36)]
    np.random.seed()
    return data

def generate_sample_timestamps():
    """Generate sample timestamps"""
    now = datetime.now()
    timestamps = []
    for i in range(24, 0, -1):
        timestamps.append((now - timedelta(hours=i)).strftime('%I %p'))
    for i in range(1, 13):
        timestamps.append((now + timedelta(hours=i)).strftime('%I %p'))
    return timestamps

# Routes
@app.route('/')
def index():
    return render_template('overview.html')

@app.route('/traffic-forecast')
def traffic_forecast():
    return render_template('traffic_forecast.html')

@app.route('/load-balancing')
def load_balancing():
    return render_template('load_balancing.html')

@app.route('/performance-comparison')
def performance_comparison():
    return render_template('performance_comparison.html')

# API Endpoints
@app.route('/api/metrics')
def get_metrics():
    return jsonify(sim_manager.current_metrics)

@app.route('/api/forecast', methods=['GET'])
def get_forecast():
    forecast_path = DATA_PATHS['forecast_csv']
    
    if not os.path.exists(forecast_path):
        return jsonify({
            'actual': generate_sample_forecast_data('actual'),
            'predicted': generate_sample_forecast_data('predicted'),
            'timestamps': generate_sample_timestamps()
        })
    
    try:
        df = pd.read_csv(forecast_path)
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time')
        
        last_24h = df.tail(24)
        actual = last_24h['actual'].tolist() if 'actual' in last_24h.columns else []
        predicted = last_24h['predicted'].tolist() if 'predicted' in last_24h.columns else []
        
        if 'forecast_t+1' in last_24h.columns:
            forecast_values = last_24h['forecast_t+1'].tail(12).tolist()
            predicted.extend(forecast_values)
        
        timestamps = generate_sample_timestamps()
        
        # Ensure we have at least 36 data points
        while len(actual) < 36:
            actual.append(actual[-1] if len(actual) > 0 else 1.0)
        while len(predicted) < 36:
            predicted.append(predicted[-1] if len(predicted) > 0 else 1.0)
        while len(timestamps) < 36:
            timestamps.append(f"{len(timestamps)}h")
        
        return jsonify({
            'actual': actual[:36],
            'predicted': predicted[:36],
            'timestamps': timestamps[:36]
        })
    except Exception as e:
        logger.error(f"Error loading forecast: {e}")
        return jsonify({
            'actual': generate_sample_forecast_data('actual'),
            'predicted': generate_sample_forecast_data('predicted'),
            'timestamps': generate_sample_timestamps()
        })

@app.route('/api/load-balancing/status')
def get_load_balancing_status():
    try:
        if sim_manager.dqn_agent is None or not MODELS_AVAILABLE:
            import random
            return jsonify({
                'episode': 1482,
                'reward': round(random.uniform(0.95, 0.99), 3),
                'epsilon': 0.05,
                'chosen_link': f'Link {random.randint(1, 3)}',
                'status': 'Demo Mode'
            })
        
        if sim_manager.sdn_env is not None:
            try:
                state = sim_manager.sdn_env.reset()
                action = sim_manager.dqn_agent.select_action(state, training=False)
                link_id = f'Link {action + 1}'
            except:
                link_id = 'Link 2'
        else:
            link_id = 'Link 2'
        
        return jsonify({
            'episode': sim_manager.dqn_agent.episode_count if sim_manager.dqn_agent else 1482,
            'reward': 0.987,
            'epsilon': sim_manager.dqn_agent.epsilon if sim_manager.dqn_agent else 0.05,
            'chosen_link': link_id,
            'status': 'Active'
        })
    except Exception as e:
        return jsonify({
            'status': 'Demo Mode',
            'error': str(e)
        }), 200

@app.route('/api/load-balancing/traffic-distribution')
def get_traffic_distribution():
    try:
        server_loads = generate_dynamic_loads()
        links_data = []
        for link in NETWORK_LINKS:
            traffic = calculate_link_traffic(link, server_loads)
            links_data.append({
                'id': link['name'],
                'traffic': traffic,
                'selected': False
            })
        
        previous_link = sim_manager.load_balancing_state['current_link']
        chosen_link_idx = 1
        
        if sim_manager.dqn_agent and sim_manager.sdn_env and MODELS_AVAILABLE:
            try:
                state = sim_manager.sdn_env.reset()
                action = sim_manager.dqn_agent.select_action(state, training=False)
                if 0 <= action < len(links_data):
                    chosen_link_idx = action
            except:
                utilizations = [l['traffic'] / NETWORK_LINKS[i]['capacity'] 
                               for i, l in enumerate(links_data)]
                chosen_link_idx = utilizations.index(min(utilizations))
        else:
            traffic_values = [l['traffic'] for l in links_data]
            chosen_link_idx = traffic_values.index(min(traffic_values))
        
        links_data[chosen_link_idx]['selected'] = True
        current_link = links_data[chosen_link_idx]['id']
        
        if previous_link and previous_link != current_link:
            sim_manager.add_notification(
                'link_change',
                f'Load balancer switched from {previous_link} to {current_link}',
                {
                    'previous_link': previous_link,
                    'current_link': current_link,
                    'reason': 'Optimal load distribution'
                }
            )
        
        sim_manager.load_balancing_state['previous_link'] = previous_link
        sim_manager.load_balancing_state['current_link'] = current_link
        
        for link_data in links_data:
            sim_manager.load_balancing_state['link_loads'][link_data['id']] = link_data['traffic']
        
        return jsonify({
            'links': links_data,
            'timestamps': [f'-{60-i*10}s' for i in range(7)]
        })
    except Exception as e:
        logger.error(f"Error in traffic distribution: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/load-balancing/link-utilization')
def get_link_utilization():
    try:
        server_loads = generate_dynamic_loads()
        links_data = []
        previous_utilizations = sim_manager.load_balancing_state.get('link_utilizations', {})
        
        for link in NETWORK_LINKS:
            traffic = calculate_link_traffic(link, server_loads)
            utilization = round((traffic / link['capacity']) * 100, 0)
            utilization = max(5, min(99, utilization))
            
            base_util = link['base_util'] * 100
            utilization = base_util + np.random.uniform(-15, 20)
            utilization = max(5, min(99, utilization))
            
            links_data.append({
                'name': link['name'],
                'utilization': int(utilization),
                'bandwidth': round(traffic, 1),
                'capacity': link['capacity']
            })
            
            link_name = link['name']
            prev_util = previous_utilizations.get(link_name, utilization)
            
            if prev_util < 80 and utilization >= 80:
                sim_manager.add_notification(
                    'high_utilization',
                    f'⚠️ High utilization detected on {link_name}: {utilization:.0f}%',
                    {'link': link_name, 'utilization': utilization, 'threshold': 80}
                )
            elif prev_util >= 90 and utilization < 90:
                sim_manager.add_notification(
                    'utilization_recovered',
                    f'✅ Utilization recovered on {link_name}: {utilization:.0f}%',
                    {'link': link_name, 'utilization': utilization}
                )
            
            sim_manager.load_balancing_state['link_utilizations'][link_name] = utilization
        
        return jsonify({'links': links_data})
    except Exception as e:
        logger.error(f"Error in link utilization: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/comparison')
def get_comparison():
    results_path = DATA_PATHS['results_csv']
    
    if os.path.exists(results_path):
        try:
            df = pd.read_csv(results_path)
            if 'Algorithm' in df.columns:
                df = df[df['Algorithm'] != 'TFT_Prediction']
                algorithms = df['Algorithm'].tolist() if len(df) > 0 else []
                
                if len(algorithms) > 0:
                    # Ensure all lists have the same length
                    throughput = df['Avg_Throughput'].tolist() if 'Avg_Throughput' in df.columns else []
                    latency = df['Avg_Latency'].tolist() if 'Avg_Latency' in df.columns else []
                    packet_loss = df['Avg_Packet_Loss'].tolist() if 'Avg_Packet_Loss' in df.columns else []
                    jitter = df['Std_Latency'].tolist() if 'Std_Latency' in df.columns else []
                    
                    # Pad with default values if needed
                    while len(throughput) < len(algorithms):
                        throughput.append(1000)
                    while len(latency) < len(algorithms):
                        latency.append(30)
                    while len(packet_loss) < len(algorithms):
                        packet_loss.append(0.2)
                    while len(jitter) < len(algorithms):
                        jitter.append(8)
                    
                    return jsonify({
                        'algorithms': algorithms,
                        'throughput': throughput[:len(algorithms)],
                        'latency': latency[:len(algorithms)],
                        'packet_loss': packet_loss[:len(algorithms)],
                        'jitter': jitter[:len(algorithms)]
                    })
        except Exception as e:
            logger.error(f"Error loading comparison data: {e}")
    
    # Return default sample data
    return jsonify({
        'algorithms': ['Round Robin (RR)', 'Weighted RR (WRR)', 'DQN'],
        'throughput': [980, 1085, 1250],
        'latency': [45, 32, 25],
        'packet_loss': [0.5, 0.3, 0.1],
        'jitter': [12, 8, 4]
    })

@app.route('/api/simulation/start', methods=['POST'])
def start_simulation():
    if sim_manager.start():
        return jsonify({'status': 'started', 'message': 'Simulation started'})
    return jsonify({'status': 'already_running', 'message': 'Simulation is already running'})

@app.route('/api/simulation/stop', methods=['POST'])
def stop_simulation():
    if sim_manager.stop():
        return jsonify({'status': 'stopped', 'message': 'Simulation stopped'})
    return jsonify({'status': 'not_running', 'message': 'Simulation is not running'})

@app.route('/api/load-balancing/notifications')
def get_notifications():
    recent_notifications = sim_manager.load_balancing_state['notifications'][-20:]
    return jsonify({'notifications': recent_notifications})

@app.route('/api/servers')
def get_servers():
    try:
        server_loads = generate_dynamic_loads()
        servers_data = []
        for server in SERVERS:
            load = server_loads.get(server['id'], 0.5)
            servers_data.append({
                'id': server['id'],
                'name': server['name'],
                'load': round(load * 100, 1),
                'status': 'active' if load < 0.9 else 'overloaded'
            })
        return jsonify({'servers': servers_data})
    except Exception as e:
        return jsonify({'servers': [], 'error': str(e)}), 200

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'models_loaded': MODELS_AVAILABLE and sim_manager.dqn_agent is not None,
        'simulation_running': sim_manager.running,
        'servers_count': len(SERVERS),
        'links_count': len(NETWORK_LINKS)
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create necessary directories
    print("=" * 60)
    print("AI-Powered SDN Load Balancing Dashboard")
    print("=" * 60)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        sim_manager.stop()
    except Exception as e:
        print(f"\n\nError starting server: {e}")
