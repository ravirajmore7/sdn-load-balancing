# SDN Load Balancing with TFT and DQN

This project implements an intelligent load balancing system for Software-Defined Networks (SDN) using Temporal Fusion Transformer (TFT) for traffic prediction and Deep Q-Network (DQN) for routing decisions.

## Architecture

The system consists of:
1. **Mininet**: Network topology simulation (Fat-tree topology with 16 hosts)
2. **Ryu Controller**: SDN controller with statistics collection
3. **TFT Model**: Traffic forecasting using Temporal Fusion Transformer
4. **DQN Agent**: Reinforcement learning agent for optimal routing decisions
5. **Evaluation**: Comparison with baseline algorithms (Round-Robin, Weighted Round-Robin)

## Project Structure

```
sdn-tft-dqn/
├─ README.md
├─ requirements.txt
├─ env_setup.sh
├─ topology/
│  └─ fat_tree_topo.py
├─ ryu_app/
│  └─ ryu_stats_collector.py
├─ traffic/
│  ├─ generate_traffic.sh
│  └─ traffic_profiles/
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ predictions/
├─ models/
│  ├─ tft_model.py
│  └─ dqn_agent.py
├─ gym_env/
│  └─ sdn_env.py
├─ notebooks/
│  └─ analysis.ipynb
├─ experiments/
│  └─ evaluate.py
└─ utils/
   └─ preprocessing.py
```

## Setup

### Prerequisites
- Ubuntu 20.04+ (recommended) or Linux environment
- Python 3.8+
- sudo access for Mininet installation

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sdn-tft-dqn
```

2. Run the setup script:
```bash
chmod +x env_setup.sh
sudo ./env_setup.sh
```

3. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage

### Web Dashboard (Recommended)

Start the web dashboard for interactive visualization:

```bash
# Install web dependencies
pip install flask flask-cors flask-socketio

# Start the web server
python app.py
```

Access the dashboard at: `http://localhost:5000`

See [DASHBOARD_README.md](DASHBOARD_README.md) for detailed dashboard documentation.

### Command Line Workflow

#### 1. Start the SDN Environment

Terminal 1 - Start Ryu controller:
```bash
ryu-manager ryu_app/ryu_stats_collector.py
```

Terminal 2 - Start Mininet topology:
```bash
sudo python3 topology/fat_tree_topo.py
```

#### 2. Generate Traffic

Terminal 3 - Run traffic generator:
```bash
chmod +x traffic/generate_traffic.sh
./traffic/generate_traffic.sh
```

#### 3. Preprocess Data

```bash
python3 utils/preprocessing.py
```

#### 4. Train TFT Model

```bash
python3 models/tft_model.py
```

#### 5. Train DQN Agent

```bash
python3 models/dqn_agent.py
```

#### 6. Evaluate and Compare

```bash
python3 experiments/evaluate.py
```

### Complete Experiment Run

Alternatively, use the automated script:
```bash
chmod +x run_experiment.sh
./run_experiment.sh
```

## Hyperparameters

### TFT Model
- `batch_size`: 128
- `max_encoder_length`: 24
- `max_prediction_length`: 12
- `hidden_size`: 8
- `attention_head_size`: 1
- `dropout`: 0.1
- `learning_rate`: 6.6e-5

### DQN Agent
- `episodes`: 1000
- `replay_buffer_size`: 10,000
- `batch_size`: 64
- `learning_rate`: 0.003
- `gamma`: 0.99
- `epsilon_start`: 1.0
- `epsilon_end`: 0.01
- `epsilon_decay`: 0.995
- `target_update_frequency`: 10 episodes

## Results

Results are saved in:
- Model checkpoints: `models/tft.ckpt`, `models/dqn_best.pth`
- Predictions: `data/predictions/tft_forecast.csv`
- Evaluation metrics: `experiments/results.csv`
- Visualizations: `notebooks/analysis.ipynb`

## Citation

If you use this code, please cite the original paper:
[Add paper citation here]

## License

[Add license information]

## Contact

[Add contact information]

