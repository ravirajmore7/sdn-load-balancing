#!/usr/bin/env python3
"""
Evaluation script for SDN Load Balancing
Compares DQN with baseline algorithms (Round-Robin, Weighted Round-Robin)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from typing import Dict, List, Tuple
import torch

# Import environment and agent
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gym_env.sdn_env import SDNEnv
from models.dqn_agent import DQNAgent

class RoundRobinBaseline:
    """Round-Robin Load Balancing"""
    
    def __init__(self, n_links):
        self.n_links = n_links
        self.current_link = 0
    
    def select_link(self, state):
        """Select next link in round-robin fashion"""
        link = self.current_link
        self.current_link = (self.current_link + 1) % self.n_links
        return link

class WeightedRoundRobinBaseline:
    """Weighted Round-Robin Load Balancing"""
    
    def __init__(self, n_links, weights=None):
        self.n_links = n_links
        if weights is None:
            # Default: equal weights
            self.weights = np.ones(n_links) / n_links
        else:
            self.weights = np.array(weights)
            self.weights = self.weights / self.weights.sum()
        
        self.current_weights = self.weights.copy()
        self.link_counts = np.zeros(n_links)
    
    def select_link(self, state):
        """Select link based on weighted round-robin"""
        # Select link with highest remaining weight
        link = np.argmax(self.current_weights)
        
        # Update weights
        self.current_weights[link] -= 1.0 / self.n_links
        self.link_counts[link] += 1
        
        # Reset weights if all exhausted
        if np.all(self.current_weights <= 0):
            self.current_weights = self.weights.copy()
        
        return link

def evaluate_algorithm(env, algorithm, n_episodes=10, algorithm_name="Algorithm"):
    """
    Evaluate an algorithm on the environment
    
    Args:
        env: Gym environment
        algorithm: Algorithm object with select_link method
        n_episodes: Number of episodes to run
        algorithm_name: Name of algorithm for logging
    
    Returns:
        metrics: Dictionary of metrics
    """
    all_rewards = []
    all_throughputs = []
    all_latencies = []
    all_packet_losses = []
    
    print(f"\nEvaluating {algorithm_name}...")
    
    for episode in range(n_episodes):
        state = env.reset()
        episode_reward = 0
        episode_throughputs = []
        episode_latencies = []
        episode_packet_losses = []
        done = False
        
        while not done:
            # Select action
            if hasattr(algorithm, 'select_link'):
                action = algorithm.select_link(state)
            elif hasattr(algorithm, 'select_action'):
                action = algorithm.select_action(state, training=False)
            else:
                action = env.action_space.sample()
            
            # Take step
            next_state, reward, done, info = env.step(action)
            
            episode_reward += reward
            episode_throughputs.append(info.get('throughput', 0.0))
            episode_latencies.append(info.get('latency', 0.0))
            episode_packet_losses.append(info.get('packet_loss', 0.0))
            
            state = next_state
        
        all_rewards.append(episode_reward)
        all_throughputs.extend(episode_throughputs)
        all_latencies.extend(episode_latencies)
        all_packet_losses.extend(episode_packet_losses)
        
        if (episode + 1) % 5 == 0:
            print(f"  Episode {episode + 1}/{n_episodes}, Reward: {episode_reward:.4f}")
    
    metrics = {
        'algorithm': algorithm_name,
        'avg_reward': np.mean(all_rewards),
        'std_reward': np.std(all_rewards),
        'avg_throughput': np.mean(all_throughputs) if all_throughputs else 0.0,
        'std_throughput': np.std(all_throughputs) if all_throughputs else 0.0,
        'avg_latency': np.mean(all_latencies) if all_latencies else 0.0,
        'std_latency': np.std(all_latencies) if all_latencies else 0.0,
        'avg_packet_loss': np.mean(all_packet_losses) if all_packet_losses else 0.0,
        'std_packet_loss': np.std(all_packet_losses) if all_packet_losses else 0.0,
        'total_episodes': n_episodes,
        'rewards': all_rewards,
        'throughputs': all_throughputs,
        'latencies': all_latencies,
        'packet_losses': all_packet_losses
    }
    
    return metrics

def compute_tft_metrics(forecast_csv='data/predictions/tft_forecast.csv'):
    """Compute TFT prediction metrics (MAE, MAPE, R²)"""
    if not os.path.exists(forecast_csv):
        print(f"Warning: Forecast file not found: {forecast_csv}")
        return {}
    
    df = pd.read_csv(forecast_csv)
    
    if 'actual' not in df.columns or 'predicted' not in df.columns:
        print("Warning: Forecast file missing 'actual' or 'predicted' columns")
        return {}
    
    actual = df['actual'].values
    predicted = df['predicted'].values
    
    # Remove NaN values
    mask = ~(np.isnan(actual) | np.isnan(predicted))
    actual = actual[mask]
    predicted = predicted[mask]
    
    if len(actual) == 0:
        return {}
    
    # MAE
    mae = np.mean(np.abs(actual - predicted))
    
    # MAPE (avoid division by zero)
    mape = np.mean(np.abs((actual - predicted) / (actual + 1e-8))) * 100
    
    # R²
    ss_res = np.sum((actual - predicted) ** 2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    r2 = 1 - (ss_res / (ss_tot + 1e-8))
    
    return {
        'mae': mae,
        'mape': mape,
        'r2': r2
    }

def plot_results(results: List[Dict], save_dir='experiments'):
    """Plot comparison results"""
    os.makedirs(save_dir, exist_ok=True)
    
    algorithms = [r['algorithm'] for r in results]
    
    # Plot 1: Average Rewards
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    rewards = [r['avg_reward'] for r in results]
    stds = [r['std_reward'] for r in results]
    plt.bar(algorithms, rewards, yerr=stds, capsize=5)
    plt.title('Average Reward Comparison')
    plt.ylabel('Reward')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Average Throughput
    plt.subplot(2, 2, 2)
    throughputs = [r['avg_throughput'] for r in results]
    stds = [r['std_throughput'] for r in results]
    plt.bar(algorithms, throughputs, yerr=stds, capsize=5)
    plt.title('Average Throughput Comparison')
    plt.ylabel('Throughput (kbps)')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Plot 3: Average Latency
    plt.subplot(2, 2, 3)
    latencies = [r['avg_latency'] for r in results]
    stds = [r['std_latency'] for r in results]
    plt.bar(algorithms, latencies, yerr=stds, capsize=5)
    plt.title('Average Latency Comparison')
    plt.ylabel('Latency (ms)')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Plot 4: Average Packet Loss
    plt.subplot(2, 2, 4)
    packet_losses = [r['avg_packet_loss'] for r in results]
    stds = [r['std_packet_loss'] for r in results]
    plt.bar(algorithms, packet_losses, yerr=stds, capsize=5)
    plt.title('Average Packet Loss Comparison')
    plt.ylabel('Packet Loss')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'comparison_results.png'), dpi=300, bbox_inches='tight')
    print(f"Plots saved to {save_dir}/comparison_results.png")
    
    # Plot reward over episodes
    plt.figure(figsize=(10, 6))
    for result in results:
        if 'rewards' in result and len(result['rewards']) > 0:
            plt.plot(result['rewards'], label=result['algorithm'], alpha=0.7)
    plt.xlabel('Episode')
    plt.ylabel('Reward')
    plt.title('Reward Over Episodes')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(save_dir, 'rewards_over_episodes.png'), dpi=300, bbox_inches='tight')
    print(f"Reward plot saved to {save_dir}/rewards_over_episodes.png")

def save_results_csv(results: List[Dict], tft_metrics: Dict, save_path='experiments/results.csv'):
    """Save results to CSV"""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Prepare data
    data = []
    for result in results:
        data.append({
            'Algorithm': result['algorithm'],
            'Avg_Reward': result['avg_reward'],
            'Std_Reward': result['std_reward'],
            'Avg_Throughput': result['avg_throughput'],
            'Std_Throughput': result['std_throughput'],
            'Avg_Latency': result['avg_latency'],
            'Std_Latency': result['std_latency'],
            'Avg_Packet_Loss': result['avg_packet_loss'],
            'Std_Packet_Loss': result['std_packet_loss'],
            'Episodes': result['total_episodes']
        })
    
    df = pd.DataFrame(data)
    
    # Add TFT metrics if available
    if tft_metrics:
        tft_row = {
            'Algorithm': 'TFT_Prediction',
            'MAE': tft_metrics.get('mae', 'N/A'),
            'MAPE': tft_metrics.get('mape', 'N/A'),
            'R2': tft_metrics.get('r2', 'N/A')
        }
        df = pd.concat([df, pd.DataFrame([tft_row])], ignore_index=True)
    
    df.to_csv(save_path, index=False)
    print(f"Results saved to {save_path}")

def main():
    """Main evaluation function"""
    print("=== SDN Load Balancing Evaluation ===\n")
    
    # Create environment
    env = SDNEnv(n_links=16, episode_length=100)
    
    results = []
    
    # 1. Evaluate Round-Robin
    rr = RoundRobinBaseline(n_links=16)
    rr_metrics = evaluate_algorithm(env, rr, n_episodes=10, algorithm_name="Round-Robin")
    results.append(rr_metrics)
    
    # 2. Evaluate Weighted Round-Robin
    wrr = WeightedRoundRobinBaseline(n_links=16)
    wrr_metrics = evaluate_algorithm(env, wrr, n_episodes=10, algorithm_name="Weighted Round-Robin")
    results.append(wrr_metrics)
    
    # 3. Evaluate DQN (if model exists)
    dqn_model_path = 'models/dqn_best.pth'
    if os.path.exists(dqn_model_path):
        state_dim = env.observation_space.shape[0]
        action_dim = env.action_space.n
        
        dqn_agent = DQNAgent(
            state_dim=state_dim,
            action_dim=action_dim,
            lr=0.003,
            gamma=0.99,
            epsilon_start=0.0,  # No exploration during evaluation
            epsilon_end=0.0,
            epsilon_decay=1.0
        )
        dqn_agent.load(dqn_model_path)
        dqn_agent.epsilon = 0.0  # Disable exploration
        
        dqn_metrics = evaluate_algorithm(env, dqn_agent, n_episodes=10, algorithm_name="DQN")
        results.append(dqn_metrics)
    else:
        print(f"\nWarning: DQN model not found at {dqn_model_path}")
        print("Skipping DQN evaluation. Train the model first.")
    
    # 4. Compute TFT metrics
    tft_metrics = compute_tft_metrics()
    if tft_metrics:
        print(f"\nTFT Prediction Metrics:")
        print(f"  MAE: {tft_metrics['mae']:.4f}")
        print(f"  MAPE: {tft_metrics['mape']:.2f}%")
        print(f"  R²: {tft_metrics['r2']:.4f}")
    
    # 5. Print summary
    print("\n=== Evaluation Summary ===")
    for result in results:
        print(f"\n{result['algorithm']}:")
        print(f"  Avg Reward: {result['avg_reward']:.4f} ± {result['std_reward']:.4f}")
        print(f"  Avg Throughput: {result['avg_throughput']:.4f} ± {result['std_throughput']:.4f}")
        print(f"  Avg Latency: {result['avg_latency']:.4f} ± {result['std_latency']:.4f}")
        print(f"  Avg Packet Loss: {result['avg_packet_loss']:.4f} ± {result['std_packet_loss']:.4f}")
    
    # 6. Plot and save results
    plot_results(results)
    save_results_csv(results, tft_metrics)
    
    print("\n=== Evaluation Complete ===")

if __name__ == '__main__':
    main()

