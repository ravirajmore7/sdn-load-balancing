import pytest
import json

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data

def test_get_metrics(client):
    """Test metrics endpoint"""
    response = client.get('/api/metrics')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'throughput' in data
    assert 'latency' in data
    assert 'packet_loss' in data

def test_get_forecast(client):
    """Test forecast endpoint"""
    response = client.get('/api/forecast')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'actual' in data
    assert 'predicted' in data
    assert 'timestamps' in data
    assert len(data['actual']) == len(data['timestamps'])

def test_load_balancing_status(client):
    """Test load balancing status endpoint"""
    response = client.get('/api/load-balancing/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert 'chosen_link' in data

def test_traffic_distribution(client):
    """Test traffic distribution endpoint"""
    response = client.get('/api/load-balancing/traffic-distribution')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'links' in data
    assert len(data['links']) > 0
    assert 'traffic' in data['links'][0]

def test_link_utilization(client):
    """Test link utilization endpoint"""
    response = client.get('/api/load-balancing/link-utilization')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'links' in data
    assert len(data['links']) > 0
    assert 'utilization' in data['links'][0]

def test_simulation_control(client):
    """Test simulation start/stop"""
    # Start simulation
    response = client.post('/api/simulation/start')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] in ['started', 'already_running']
    
    # Stop simulation
    response = client.post('/api/simulation/stop')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] in ['stopped', 'not_running']
