#!/usr/bin/env python3
"""
Deep Q-Network (DQN) Agent for SDN Load Balancing
Implements DQN with experience replay and target network
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random
from collections import deque
import os
from typing import Tuple, List

class DQNNetwork(nn.Module):
    """DQN Neural Network"""
    
    def __init__(self, state_dim, action_dim, hidden_sizes=[128, 128]):
        """
        Initialize DQN network
        
        Args:
            state_dim: Dimension of state space
            action_dim: Dimension of action space
            hidden_sizes: List of hidden layer sizes
        """
        super(DQNNetwork, self).__init__()
        
        layers = []
        input_size = state_dim
        
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(input_size, hidden_size))
            layers.append(nn.ReLU())
            input_size = hidden_size
        
        layers.append(nn.Linear(input_size, action_dim))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        """Forward pass"""
        return self.network(x)

class ReplayBuffer:
    """Experience Replay Buffer"""
    
    def __init__(self, capacity=10000):
        """
        Initialize replay buffer
        
        Args:
            capacity: Maximum number of transitions to store
        """
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        """Add transition to buffer"""
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        """Sample a batch of transitions"""
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        return (
            torch.FloatTensor(states),
            torch.LongTensor(actions),
            torch.FloatTensor(rewards),
            torch.FloatTensor(next_states),
            torch.BoolTensor(dones)
        )
    
    def __len__(self):
        return len(self.buffer)

class DQNAgent:
    """DQN Agent"""
    
    def __init__(self, state_dim, action_dim, lr=0.003, gamma=0.99,
                 epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995,
                 replay_buffer_size=10000, batch_size=64, target_update_freq=10,
                 device='cpu'):
        """
        Initialize DQN agent
        
        Args:
            state_dim: Dimension of state space
            action_dim: Dimension of action space
            lr: Learning rate
            gamma: Discount factor
            epsilon_start: Initial epsilon for epsilon-greedy
            epsilon_end: Final epsilon
            epsilon_decay: Epsilon decay rate
            replay_buffer_size: Size of replay buffer
            batch_size: Batch size for training
            target_update_freq: Frequency of target network updates (in episodes)
            device: Device to run on ('cpu' or 'cuda')
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.device = torch.device(device)
        
        # Networks
        self.q_network = DQNNetwork(state_dim, action_dim).to(self.device)
        self.target_network = DQNNetwork(state_dim, action_dim).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.target_network.eval()
        
        # Optimizer
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        
        # Replay buffer
        self.replay_buffer = ReplayBuffer(replay_buffer_size)
        
        # Training stats
        self.training_losses = []
        self.episode_count = 0
    
    def select_action(self, state, training=True):
        """
        Select action using epsilon-greedy policy
        
        Args:
            state: Current state
            training: Whether in training mode (uses epsilon-greedy)
        
        Returns:
            action: Selected action
        """
        if training and random.random() < self.epsilon:
            return random.randrange(self.action_dim)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.q_network(state_tensor)
            return q_values.argmax().item()
    
    def push(self, state, action, reward, next_state, done):
        """Add transition to replay buffer"""
        self.replay_buffer.push(state, action, reward, next_state, done)
    
    def learn(self):
        """Train the agent on a batch from replay buffer"""
        if len(self.replay_buffer) < self.batch_size:
            return
        
        # Sample batch
        states, actions, rewards, next_states, dones = self.replay_buffer.sample(self.batch_size)
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)
        
        # Current Q values
        q_values = self.q_network(states)
        q_value = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Next Q values from target network
        with torch.no_grad():
            next_q_values = self.target_network(next_states)
            next_q_value = next_q_values.max(1)[0]
            target_q_value = rewards + (self.gamma * next_q_value * ~dones)
        
        # Compute loss
        loss = F.mse_loss(q_value, target_q_value)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        self.training_losses.append(loss.item())
        return loss.item()
    
    def update_target_network(self):
        """Update target network with current Q-network weights"""
        self.target_network.load_state_dict(self.q_network.state_dict())
    
    def update_epsilon(self):
        """Decay epsilon"""
        if self.epsilon > self.epsilon_end:
            self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
    
    def update_target_net_periodically(self):
        """Update target network if it's time"""
        self.episode_count += 1
        if self.episode_count % self.target_update_freq == 0:
            self.update_target_network()
            print(f"Target network updated at episode {self.episode_count}")
    
    def save(self, filepath):
        """Save model checkpoint"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        torch.save({
            'q_network_state_dict': self.q_network.state_dict(),
            'target_network_state_dict': self.target_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'episode_count': self.episode_count,
        }, filepath)
        print(f"Model saved to {filepath}")
    
    def load(self, filepath):
        """Load model checkpoint"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.q_network.load_state_dict(checkpoint['q_network_state_dict'])
        self.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint.get('epsilon', self.epsilon_start)
        self.episode_count = checkpoint.get('episode_count', 0)
        print(f"Model loaded from {filepath}")

def train_dqn(env, agent, n_episodes=1000, save_freq=100, model_dir='models'):
    """
    Train DQN agent
    
    Args:
        env: Gym environment
        agent: DQN agent
        n_episodes: Number of training episodes
        save_freq: Frequency of saving model (in episodes)
        model_dir: Directory to save models
    """
    os.makedirs(model_dir, exist_ok=True)
    
    episode_rewards = []
    best_reward = float('-inf')
    
    print("Starting DQN training...")
    print(f"Episodes: {n_episodes}, Batch size: {agent.batch_size}, LR: {agent.lr}")
    
    for episode in range(n_episodes):
        state = env.reset()
        episode_reward = 0
        done = False
        steps = 0
        
        while not done:
            # Select action
            action = agent.select_action(state, training=True)
            
            # Take step
            next_state, reward, done, info = env.step(action)
            
            # Store transition
            agent.push(state, action, reward, next_state, done)
            
            # Train
            loss = agent.learn()
            
            state = next_state
            episode_reward += reward
            steps += 1
        
        # Update epsilon
        agent.update_epsilon()
        
        # Update target network periodically
        agent.update_target_net_periodically()
        
        episode_rewards.append(episode_reward)
        
        # Print progress
        if (episode + 1) % 10 == 0:
            avg_reward = np.mean(episode_rewards[-10:])
            print(f"Episode {episode + 1}/{n_episodes}, "
                  f"Avg Reward: {avg_reward:.4f}, "
                  f"Epsilon: {agent.epsilon:.4f}, "
                  f"Steps: {steps}")
        
        # Save best model
        if episode_reward > best_reward:
            best_reward = episode_reward
            agent.save(os.path.join(model_dir, 'dqn_best.pth'))
        
        # Periodic save
        if (episode + 1) % save_freq == 0:
            agent.save(os.path.join(model_dir, f'dqn_episode_{episode + 1}.pth'))
    
    print("Training complete!")
    return episode_rewards

if __name__ == '__main__':
    from gym_env.sdn_env import SDNEnv
    
    # Create environment
    env = SDNEnv(n_links=16, episode_length=100)
    
    # Create agent
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.n
    
    agent = DQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        lr=0.003,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay=0.995,
        replay_buffer_size=10000,
        batch_size=64,
        target_update_freq=10
    )
    
    # Train
    rewards = train_dqn(env, agent, n_episodes=1000)
    
    print(f"Average reward: {np.mean(rewards):.4f}")
    print(f"Best reward: {max(rewards):.4f}")

