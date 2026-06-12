#!/bin/bash
# SDN TFT-DQN Environment Setup Script
# Run with: sudo ./env_setup.sh

set -e

echo "=== SDN TFT-DQN Environment Setup ==="

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and basic tools
echo "Installing Python and basic tools..."
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Install Mininet and dependencies
echo "Installing Mininet and OpenVSwitch..."
sudo apt install -y mininet openvswitch-switch

# Install Ryu controller
echo "Installing Ryu SDN controller..."
pip3 install ryu

# Install ML stack
echo "Installing PyTorch and ML libraries..."
# Check for CUDA availability (optional - adjust based on your system)
# For CPU-only: use default pip install
# For CUDA: uncomment and adjust version
# pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

pip3 install torch torchvision torchaudio

# Install PyTorch Lightning and Forecasting
echo "Installing PyTorch Lightning and Forecasting..."
pip3 install pytorch-lightning pytorch-forecasting

# Install data science libraries
echo "Installing data science libraries..."
pip3 install pandas numpy scikit-learn matplotlib seaborn networkx

# Install Gym for RL
echo "Installing Gym for reinforcement learning..."
pip3 install gym gymnasium

# Install utilities
echo "Installing utilities..."
pip3 install tabulate jupyterlab tqdm joblib

# Install iperf3 for traffic generation
echo "Installing iperf3..."
sudo apt install -y iperf3

# Create virtual environment (optional but recommended)
echo "Creating Python virtual environment..."
python3 -m venv venv
echo "To activate: source venv/bin/activate"

# Verify installations
echo ""
echo "=== Verification ==="
echo "Python version: $(python3 --version)"
echo "Pip version: $(pip3 --version)"
echo "Mininet version: $(mn --version 2>/dev/null || echo 'Mininet installed')"
echo "Ryu version: $(ryu-manager --version 2>/dev/null || echo 'Ryu installed')"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Install requirements: pip install -r requirements.txt"
echo "3. Start Ryu controller: ryu-manager ryu_app/ryu_stats_collector.py"
echo "4. Start Mininet: sudo python3 topology/fat_tree_topo.py"

