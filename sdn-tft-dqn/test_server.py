#!/usr/bin/env python3
"""
Quick test script to verify the server is working
"""

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install it with: pip install requests")
    exit(1)

import json

BASE_URL = "http://localhost:5000"

def test_endpoint(endpoint, description):
    """Test an API endpoint"""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        if response.status_code == 200:
            print(f"✓ {description}: OK")
            return True
        else:
            print(f"✗ {description}: Status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ {description}: Server not running")
        return False
    except Exception as e:
        print(f"✗ {description}: Error - {e}")
        return False

def main():
    print("=" * 60)
    print("SDN Dashboard Server Test")
    print("=" * 60)
    print(f"Testing server at: {BASE_URL}\n")
    
    endpoints = [
        ("/api/health", "Health Check"),
        ("/api/metrics", "Metrics"),
        ("/api/forecast", "Forecast"),
        ("/api/load-balancing/status", "Load Balancing Status"),
        ("/api/load-balancing/traffic-distribution", "Traffic Distribution"),
        ("/api/load-balancing/link-utilization", "Link Utilization"),
        ("/api/comparison", "Comparison"),
    ]
    
    results = []
    for endpoint, desc in endpoints:
        results.append(test_endpoint(endpoint, desc))
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Server is working correctly.")
    else:
        print("⚠ Some tests failed. Check server logs for details.")
    print("=" * 60)

if __name__ == "__main__":
    main()

