#!/bin/bash
# Traffic Generation Script for SDN Load Balancing
# Run this script from within Mininet CLI or as separate processes

echo "=== Starting Traffic Generation ==="

# Configuration
DURATION=300  # 5 minutes
SERVER_PORT=5001
HTTP_PORT=80

# Function to start iperf3 server on a host
start_iperf_server() {
    local host=$1
    echo "Starting iperf3 server on $host"
    $host iperf3 -s -p $SERVER_PORT > /dev/null 2>&1 &
}

# Function to start HTTP server on a host
start_http_server() {
    local host=$1
    echo "Starting HTTP server on $host"
    $host python3 -m http.server $HTTP_PORT > /dev/null 2>&1 &
}

# Function to generate iperf3 traffic
generate_iperf_traffic() {
    local client=$1
    local server_ip=$2
    local bandwidth=$3
    echo "Generating iperf3 traffic: $client -> $server_ip ($bandwidth)"
    $client iperf3 -c $server_ip -p $SERVER_PORT -t $DURATION -b $bandwidth > /dev/null 2>&1 &
}

# Function to generate HTTP traffic
generate_http_traffic() {
    local client=$1
    local server_ip=$2
    echo "Generating HTTP traffic: $client -> $server_ip"
    $client wget -O /dev/null http://$server_ip:$HTTP_PORT/index.html > /dev/null 2>&1 &
    # Repeat periodically
    for i in {1..10}; do
        sleep 30
        $client wget -O /dev/null http://$server_ip:$HTTP_PORT/index.html > /dev/null 2>&1 &
    done
}

# Function to generate DNS traffic
generate_dns_traffic() {
    local client=$1
    local server_ip=$2
    echo "Generating DNS traffic: $client -> $server_ip"
    for i in {1..50}; do
        $client dig @$server_ip www.example.com > /dev/null 2>&1
        sleep 5
    done &
}

# Function to generate ICMP traffic
generate_icmp_traffic() {
    local client=$1
    local server_ip=$2
    echo "Generating ICMP traffic: $client -> $server_ip"
    $client ping -c 100 $server_ip > /dev/null 2>&1 &
}

# Main traffic generation
# Note: This script assumes you're running it from within Mininet CLI
# or have access to host commands

echo "Traffic generation profiles:"
echo "1. High bandwidth (iperf3): h1->h16, h2->h15, h3->h14, h4->h13"
echo "2. Medium bandwidth (iperf3): h5->h12, h6->h11, h7->h10, h8->h9"
echo "3. HTTP traffic: h9->h1, h10->h2"
echo "4. DNS traffic: h11->h3, h12->h4"
echo "5. ICMP traffic: h13->h5, h14->h6"

# Example usage in Mininet CLI:
# In Mininet CLI, you would run:
# h1 iperf3 -s -p 5001 &
# h16 iperf3 -c 10.0.0.1 -p 5001 -t 300 -b 500M &

echo ""
echo "=== Traffic Generation Script Ready ==="
echo "Run individual commands in Mininet CLI or modify this script"
echo "to automatically generate traffic patterns."

# Example automated traffic (uncomment and modify for your use case):
# start_iperf_server h1
# sleep 2
# generate_iperf_traffic h16 10.0.0.1 500M
# generate_iperf_traffic h15 10.0.0.1 300M
# generate_iperf_traffic h14 10.0.0.1 200M

