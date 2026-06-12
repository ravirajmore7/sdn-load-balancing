"""
Configuration settings for the SDN Load Balancing Dashboard
"""

# Server configuration
SERVERS = [
    {'id': 'S1', 'name': 'Server 1 (Core)', 'base_load': 0.8, 'load_variance': 0.2},
    {'id': 'S2', 'name': 'Server 2 (Edge)', 'base_load': 0.6, 'load_variance': 0.3},
    {'id': 'S3', 'name': 'Server 3 (Edge)', 'base_load': 0.7, 'load_variance': 0.25},
    {'id': 'S4', 'name': 'Server 4 (Edge)', 'base_load': 0.65, 'load_variance': 0.3},
    {'id': 'S5', 'name': 'Server 5 (Access)', 'base_load': 0.5, 'load_variance': 0.4},
    {'id': 'S6', 'name': 'Server 6 (Access)', 'base_load': 0.55, 'load_variance': 0.35},
    {'id': 'S7', 'name': 'Server 7 (Access)', 'base_load': 0.6, 'load_variance': 0.3},
    {'id': 'S8', 'name': 'Server 8 (Backup)', 'base_load': 0.4, 'load_variance': 0.2}
]

# Network links configuration
NETWORK_LINKS = [
    {'id': 'L1', 'name': 'Link 1 (S1-S2)', 'servers': ['S1', 'S2'], 'capacity': 15.0, 'base_util': 0.75},
    {'id': 'L2', 'name': 'Link 2 (S1-S3)', 'servers': ['S1', 'S3'], 'capacity': 14.0, 'base_util': 0.88},
    {'id': 'L3', 'name': 'Link 3 (S1-S4)', 'servers': ['S1', 'S4'], 'capacity': 13.0, 'base_util': 0.92},
    {'id': 'L4', 'name': 'Link 4 (S2-S5)', 'servers': ['S2', 'S5'], 'capacity': 7.0, 'base_util': 0.45},
    {'id': 'L5', 'name': 'Link 5 (S3-S6)', 'servers': ['S3', 'S6'], 'capacity': 8.0, 'base_util': 0.55},
    {'id': 'L6', 'name': 'Link 6 (S4-S7)', 'servers': ['S4', 'S7'], 'capacity': 9.0, 'base_util': 0.60},
    {'id': 'L7', 'name': 'Link 7 (S5-S8)', 'servers': ['S5', 'S8'], 'capacity': 6.0, 'base_util': 0.40},
    {'id': 'L8', 'name': 'Link 8 (S6-S7)', 'servers': ['S6', 'S7'], 'capacity': 7.5, 'base_util': 0.50}
]

# Simulation parameters
SIMULATION_CONFIG = {
    'base_throughput': 1.2,  # Tbps
    'base_latency': 12,      # ms
    'base_packet_loss': 0.05, # %
    'update_interval': 2     # seconds
}

# Paths
DATA_PATHS = {
    'processed_csv': 'data/processed/processed.csv',
    'forecast_csv': 'data/predictions/tft_forecast.csv',
    'dqn_model': 'models/dqn_best.pth',
    'results_csv': 'experiments/results.csv'
}
