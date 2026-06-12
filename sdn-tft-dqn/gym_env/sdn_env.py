#!/usr/bin/env python3
"""
Gym Environment for SDN Load Balancing
Custom environment for DQN agent training
"""

import gym
from gym import spaces
import numpy as np
import pandas as pd
import os
from typing import Tuple, Dict, Any

class SDNEnv(gym.Env):
    """
    SDN Load Balancing Environment
    
    State: For each link: [throughput_normalized, latency_norm, packet_loss_norm, forecasted_traffic_norm]
    Action: Discrete integer selecting which link to route the current flow over
    Reward: alpha * throughput - beta * latency - gamma * packet_loss
    """
    
    metadata = {'render.modes': ['human']}
    
    def __init__(self, data_csv='data/processed/processed.csv', 
                 forecast_csv='data/predictions/tft_forecast.csv',
                 n_links=16, alpha=1.0, beta=0.1, gamma=0.1,
                 episode_length=100):
        """
        Initialize environment
        
        Args:
            data_csv: Path to processed traffic data
            forecast_csv: Path to TFT forecast data
            n_links: Number of links in the network
            alpha: Reward coefficient for throughput
            beta: Reward coefficient for latency (penalty)
            gamma: Reward coefficient for packet loss (penalty)
            episode_length: Maximum steps per episode
        """
        super(SDNEnv, self).__init__()
        
        self.n_links = n_links
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.episode_length = episode_length
        
        # State: n_links * 4 features (throughput, latency, packet_loss, forecast)
        self.state_size = n_links * 4
        self.n_features_per_link = 4
        
        # Action space: select which link to use (0 to n_links-1)
        self.action_space = spaces.Discrete(n_links)
        
        # Observation space: normalized features [0, 1]
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.state_size,), dtype=np.float32
        )
        
        # Load data
        self._load_data(data_csv, forecast_csv)
        
        # Episode state
        self.current_step = 0
        self.current_state = None
        self.episode_rewards = []
        self.episode_actions = []
        
    def _load_data(self, data_csv, forecast_csv):
        """Load traffic data and forecasts"""
        if not os.path.exists(data_csv):
            raise FileNotFoundError(f"Data file not found: {data_csv}")
        
        self.data = pd.read_csv(data_csv)
        
        # Parse time if present
        if 'time' in self.data.columns:
            self.data['time'] = pd.to_datetime(self.data['time'])
            self.data = self.data.sort_values('time')
        
        # Load forecasts if available
        if os.path.exists(forecast_csv):
            self.forecasts = pd.read_csv(forecast_csv)
            if 'time' in self.forecasts.columns:
                self.forecasts['time'] = pd.to_datetime(self.forecasts['time'])
        else:
            print(f"Warning: Forecast file not found: {forecast_csv}. Using zeros for forecasts.")
            self.forecasts = None
        
        # Get unique link IDs
        if 'link_id' in self.data.columns:
            self.link_ids = self.data['link_id'].unique()[:self.n_links]
        else:
            self.link_ids = [f'link_{i}' for i in range(self.n_links)]
        
        print(f"Loaded data with {len(self.data)} rows and {len(self.link_ids)} links")
    
    def _get_state(self, step_idx):
        """
        Get state vector for current step
        
        Returns:
            state: numpy array of shape (state_size,)
        """
        # Get data for current time step
        if step_idx >= len(self.data):
            step_idx = len(self.data) - 1
        
        # Group by link_id and get latest metrics
        state = np.zeros(self.state_size, dtype=np.float32)
        
        for i, link_id in enumerate(self.link_ids):
            if i >= self.n_links:
                break
            
            # Get link data
            link_data = self.data[self.data['link_id'] == link_id]
            if len(link_data) == 0:
                # Use default values if no data
                state[i * 4:(i + 1) * 4] = [0.0, 0.0, 0.0, 0.0]
                continue
            
            # Get latest or step-specific data
            if step_idx < len(link_data):
                link_row = link_data.iloc[step_idx % len(link_data)]
            else:
                link_row = link_data.iloc[-1]
            
            # Extract features (normalized values)
            throughput = link_row.get('throughput_kbps', 0.0)
            if pd.isna(throughput):
                throughput = 0.0
            
            latency = link_row.get('latency_ms', 0.0)
            if pd.isna(latency):
                latency = 0.0
            
            packet_loss = link_row.get('packet_loss', 0.0)
            if pd.isna(packet_loss):
                packet_loss = 0.0
            
            # Get forecast (from TFT predictions)
            forecast = 0.0
            if self.forecasts is not None:
                forecast_data = self.forecasts[self.forecasts['link_id'] == link_id]
                if len(forecast_data) > 0:
                    forecast_row = forecast_data.iloc[step_idx % len(forecast_data)]
                    forecast = forecast_row.get('predicted', forecast_row.get('forecast_t+1', 0.0))
                    if pd.isna(forecast):
                        forecast = 0.0
            
            # Normalize to [0, 1] (assuming data is already normalized from preprocessing)
            # Clip to ensure [0, 1] range
            state[i * 4] = np.clip(float(throughput), 0.0, 1.0)
            state[i * 4 + 1] = np.clip(float(latency), 0.0, 1.0)
            state[i * 4 + 2] = np.clip(float(packet_loss), 0.0, 1.0)
            state[i * 4 + 3] = np.clip(float(forecast), 0.0, 1.0)
        
        return state
    
    def reset(self, seed=None) -> np.ndarray:
        """Reset environment to initial state"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.episode_rewards = []
        self.episode_actions = []
        
        # Start from random or first time step
        if seed is not None:
            np.random.seed(seed)
        start_idx = np.random.randint(0, max(1, len(self.data) - self.episode_length))
        
        self.current_state = self._get_state(start_idx)
        
        return self.current_state
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Execute one step in the environment
        
        Args:
            action: Link index to route flow through (0 to n_links-1)
        
        Returns:
            observation: Next state
            reward: Reward for this step
            done: Whether episode is finished
            info: Additional information
        """
        if action < 0 or action >= self.n_links:
            action = action % self.n_links
        
        # Get metrics for selected link
        link_idx = action
        link_id = self.link_ids[link_idx] if link_idx < len(self.link_ids) else self.link_ids[0]
        
        # Get link data for current step
        link_data = self.data[self.data['link_id'] == link_id]
        if len(link_data) > 0:
            step_data = link_data.iloc[self.current_step % len(link_data)]
            throughput = float(step_data.get('throughput_kbps', 0.0))
            latency = float(step_data.get('latency_ms', 0.0))
            packet_loss = float(step_data.get('packet_loss', 0.0))
        else:
            throughput = 0.0
            latency = 0.0
            packet_loss = 0.0
        
        # Calculate reward: alpha * throughput - beta * latency - gamma * packet_loss
        reward = (self.alpha * throughput - 
                 self.beta * latency - 
                 self.gamma * packet_loss)
        
        # Update step
        self.current_step += 1
        
        # Get next state
        next_state = self._get_state(self.current_step)
        self.current_state = next_state
        
        # Check if done
        done = (self.current_step >= self.episode_length) or (self.current_step >= len(self.data))
        
        # Store episode info
        self.episode_rewards.append(reward)
        self.episode_actions.append(action)
        
        info = {
            'throughput': throughput,
            'latency': latency,
            'packet_loss': packet_loss,
            'link_id': link_id,
            'step': self.current_step
        }
        
        return next_state, reward, done, info
    
    def render(self, mode='human'):
        """Render environment state"""
        if mode == 'human':
            print(f"Step: {self.current_step}/{self.episode_length}")
            print(f"Last reward: {self.episode_rewards[-1] if self.episode_rewards else 0:.4f}")
            print(f"Average reward: {np.mean(self.episode_rewards) if self.episode_rewards else 0:.4f}")
    
    def get_episode_stats(self):
        """Get statistics for current episode"""
        if not self.episode_rewards:
            return {}
        
        return {
            'total_reward': sum(self.episode_rewards),
            'average_reward': np.mean(self.episode_rewards),
            'episode_length': len(self.episode_rewards),
            'actions_taken': self.episode_actions
        }

