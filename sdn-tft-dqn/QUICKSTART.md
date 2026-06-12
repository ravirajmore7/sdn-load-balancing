# Quick Start Guide

## Prerequisites

- Ubuntu 20.04+ (or Linux environment)
- Python 3.8+
- sudo access
- Git

## Installation Steps

### 1. Setup Environment

```bash
# Make scripts executable
chmod +x env_setup.sh
chmod +x run_experiment.sh
chmod +x traffic/generate_traffic.sh

# Run setup (requires sudo)
sudo ./env_setup.sh

# Install Python dependencies
pip3 install -r requirements.txt
```

### 2. Collect Data (Optional - if you have real data, skip to step 3)

**Terminal 1 - Start Ryu Controller:**
```bash
ryu-manager ryu_app/ryu_stats_collector.py
```

**Terminal 2 - Start Mininet Topology:**
```bash
sudo python3 topology/fat_tree_topo.py
```

**Terminal 3 - Generate Traffic:**
```bash
# In Mininet CLI, run traffic generation commands
# Or use the traffic generation script
./traffic/generate_traffic.sh
```

Let the system run for a few minutes to collect data, then stop both terminals.

### 3. Preprocess Data

```bash
python3 utils/preprocessing.py
```

This will:
- Load raw CSV files from `data/raw/`
- Handle missing values and outliers
- Normalize features
- Create train/val splits
- Save processed data to `data/processed/`

### 4. Train TFT Model

```bash
python3 models/tft_model.py
```

This will:
- Train the Temporal Fusion Transformer model
- Save model to `models/tft.ckpt`
- Generate predictions to `data/predictions/tft_forecast.csv`

### 5. Train DQN Agent

```bash
python3 models/dqn_agent.py
```

This will:
- Train the DQN agent using the Gym environment
- Save best model to `models/dqn_best.pth`

### 6. Evaluate and Compare

```bash
python3 experiments/evaluate.py
```

This will:
- Evaluate Round-Robin baseline
- Evaluate Weighted Round-Robin baseline
- Evaluate DQN agent (if model exists)
- Compute TFT prediction metrics
- Generate comparison plots
- Save results to `experiments/results.csv`

### 7. View Analysis

```bash
# Open Jupyter notebook
jupyter lab notebooks/analysis.ipynb
```

## Automated Run

Alternatively, run everything at once:

```bash
./run_experiment.sh
```

## Troubleshooting

### Issue: Mininet not found
```bash
sudo apt install mininet
```

### Issue: Ryu not found
```bash
pip3 install ryu
```

### Issue: No data collected
- Make sure Ryu controller is running before starting Mininet
- Check that traffic is being generated
- Verify CSV files are being created in `data/raw/`

### Issue: CUDA/GPU errors
- The code defaults to CPU
- For GPU training, modify device settings in model files
- Install CUDA-compatible PyTorch if needed

### Issue: Import errors
- Make sure all dependencies are installed: `pip3 install -r requirements.txt`
- Check Python path includes project root

## File Structure

```
sdn-tft-dqn/
├── README.md              # Main documentation
├── QUICKSTART.md          # This file
├── requirements.txt       # Python dependencies
├── env_setup.sh          # Environment setup script
├── run_experiment.sh     # Complete experiment runner
├── topology/             # Mininet topology
├── ryu_app/              # Ryu SDN controller app
├── traffic/               # Traffic generation
├── data/                  # Data storage
│   ├── raw/              # Raw collected data
│   ├── processed/        # Preprocessed data
│   └── predictions/      # TFT predictions
├── models/               # Model files
├── gym_env/              # Gym environment
├── notebooks/            # Analysis notebooks
├── experiments/          # Evaluation scripts
└── utils/                # Utility functions
```

## Next Steps

1. Review the results in `experiments/results.csv`
2. Check visualizations in `experiments/comparison_results.png`
3. Analyze detailed results in `notebooks/analysis.ipynb`
4. Tune hyperparameters in model files if needed
5. Extend the system with additional features

## Support

For issues or questions, refer to the main README.md or check the code comments in each module.

