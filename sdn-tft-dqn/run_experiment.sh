#!/bin/bash
# Complete Experiment Runner Script
# Runs the full pipeline: data collection -> preprocessing -> training -> evaluation

set -e

echo "=== SDN TFT-DQN Experiment Runner ==="
echo ""

# Configuration
RYU_PORT=6633
EXPERIMENT_DURATION=300  # 5 minutes

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "Checking prerequisites..."
if ! command_exists python3; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

if ! command_exists ryu-manager; then
    echo -e "${YELLOW}Warning: ryu-manager not found. Install Ryu first.${NC}"
fi

if ! command_exists mn; then
    echo -e "${YELLOW}Warning: mininet not found. Install Mininet first.${NC}"
fi

echo -e "${GREEN}Prerequisites check complete${NC}"
echo ""

# Step 1: Preprocessing
echo "=== Step 1: Preprocessing Data ==="
if [ -d "data/raw" ] && [ "$(ls -A data/raw/*.csv 2>/dev/null)" ]; then
    echo "Processing raw data..."
    python3 utils/preprocessing.py
    echo -e "${GREEN}Preprocessing complete${NC}"
else
    echo -e "${YELLOW}Warning: No raw data found. Skipping preprocessing.${NC}"
    echo "To collect data:"
    echo "  1. Start Ryu: ryu-manager ryu_app/ryu_stats_collector.py"
    echo "  2. Start Mininet: sudo python3 topology/fat_tree_topo.py"
    echo "  3. Generate traffic using traffic/generate_traffic.sh"
fi
echo ""

# Step 2: Train TFT Model
echo "=== Step 2: Training TFT Model ==="
if [ -f "data/processed/processed.csv" ] || [ -f "data/processed/train.csv" ]; then
    echo "Training TFT model..."
    python3 models/tft_model.py
    echo -e "${GREEN}TFT training complete${NC}"
else
    echo -e "${YELLOW}Warning: No processed data found. Skipping TFT training.${NC}"
fi
echo ""

# Step 3: Train DQN Agent
echo "=== Step 3: Training DQN Agent ==="
if [ -f "data/processed/processed.csv" ] || [ -f "data/processed/train.csv" ]; then
    echo "Training DQN agent..."
    python3 models/dqn_agent.py
    echo -e "${GREEN}DQN training complete${NC}"
else
    echo -e "${YELLOW}Warning: No processed data found. Skipping DQN training.${NC}"
fi
echo ""

# Step 4: Evaluation
echo "=== Step 4: Evaluation ==="
if [ -f "models/dqn_best.pth" ] || [ -f "models/tft.ckpt" ]; then
    echo "Running evaluation..."
    python3 experiments/evaluate.py
    echo -e "${GREEN}Evaluation complete${NC}"
else
    echo -e "${YELLOW}Warning: No trained models found. Skipping evaluation.${NC}"
    echo "Train models first using steps 2 and 3."
fi
echo ""

echo "=== Experiment Complete ==="
echo ""
echo "Results saved to:"
echo "  - Models: models/tft.ckpt, models/dqn_best.pth"
echo "  - Predictions: data/predictions/tft_forecast.csv"
echo "  - Evaluation: experiments/results.csv"
echo "  - Plots: experiments/comparison_results.png"
echo ""
echo "To view analysis, open: notebooks/analysis.ipynb"

