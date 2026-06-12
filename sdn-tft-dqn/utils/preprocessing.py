#!/usr/bin/env python3
"""
Preprocessing utilities for SDN traffic data
Handles missing values, outliers, normalization, and feature engineering
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import os
import glob
import pickle
from pathlib import Path

class DataPreprocessor:
    def __init__(self, raw_data_dir='data/raw', processed_data_dir='data/processed', 
                 scaler_dir='scalers', use_minmax=True):
        """
        Initialize preprocessor
        
        Args:
            raw_data_dir: Directory containing raw CSV files
            processed_data_dir: Directory to save processed data
            scaler_dir: Directory to save scaler objects
            use_minmax: If True, use MinMaxScaler, else StandardScaler
        """
        self.raw_data_dir = raw_data_dir
        self.processed_data_dir = processed_data_dir
        self.scaler_dir = scaler_dir
        self.use_minmax = use_minmax
        
        # Create directories
        os.makedirs(processed_data_dir, exist_ok=True)
        os.makedirs(scaler_dir, exist_ok=True)
        
        # Initialize scaler
        if use_minmax:
            self.scaler = MinMaxScaler()
        else:
            self.scaler = StandardScaler()
        
        self.scaler_fitted = False
    
    def load_raw_data(self):
        """Load and concatenate all raw CSV files"""
        csv_files = glob.glob(os.path.join(self.raw_data_dir, 'traffic_*.csv'))
        
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.raw_data_dir}")
        
        print(f"Found {len(csv_files)} CSV files")
        
        dfs = []
        for file in csv_files:
            try:
                df = pd.read_csv(file, parse_dates=['time'])
                dfs.append(df)
                print(f"Loaded {file}: {len(df)} rows")
            except Exception as e:
                print(f"Error loading {file}: {e}")
        
        if not dfs:
            raise ValueError("No valid CSV files could be loaded")
        
        # Concatenate all dataframes
        df = pd.concat(dfs, ignore_index=True)
        df = df.sort_values('time')
        
        print(f"Total rows after concatenation: {len(df)}")
        return df
    
    def handle_missing_values(self, df, method='forward_fill'):
        """
        Handle missing values
        
        Args:
            df: DataFrame
            method: 'forward_fill', 'backward_fill', 'mean', 'median', or 'interpolate'
        """
        print(f"Handling missing values using {method}...")
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if method == 'forward_fill':
            df[numeric_cols] = df[numeric_cols].fillna(method='ffill')
            df[numeric_cols] = df[numeric_cols].fillna(method='bfill')  # Fill remaining with backward
        elif method == 'backward_fill':
            df[numeric_cols] = df[numeric_cols].fillna(method='bfill')
            df[numeric_cols] = df[numeric_cols].fillna(method='ffill')  # Fill remaining with forward
        elif method == 'mean':
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
        elif method == 'median':
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
        elif method == 'interpolate':
            df[numeric_cols] = df[numeric_cols].interpolate(method='linear')
            df[numeric_cols] = df[numeric_cols].fillna(method='ffill').fillna(method='bfill')
        
        # Fill any remaining NaN with 0
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        print(f"Missing values after handling: {df.isnull().sum().sum()}")
        return df
    
    def handle_outliers(self, df, method='clip', lower_percentile=0.01, upper_percentile=0.99):
        """
        Handle outliers
        
        Args:
            df: DataFrame
            method: 'clip' or 'replace'
            lower_percentile: Lower percentile for clipping
            upper_percentile: Upper percentile for clipping
        """
        print(f"Handling outliers using {method}...")
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if method == 'clip':
            for col in numeric_cols:
                lower = df[col].quantile(lower_percentile)
                upper = df[col].quantile(upper_percentile)
                df[col] = df[col].clip(lower=lower, upper=upper)
        elif method == 'replace':
            for col in numeric_cols:
                lower = df[col].quantile(lower_percentile)
                upper = df[col].quantile(upper_percentile)
                # Replace outliers with neighbor average
                mask = (df[col] < lower) | (df[col] > upper)
                df.loc[mask, col] = df[col].rolling(window=5, center=True).mean()[mask]
                # Fill any remaining NaN
                df[col] = df[col].fillna(df[col].mean())
        
        return df
    
    def normalize_features(self, df, numeric_cols=None):
        """
        Normalize numeric features
        
        Args:
            df: DataFrame
            numeric_cols: List of columns to normalize. If None, auto-detect numeric columns
        """
        if numeric_cols is None:
            numeric_cols = ['tx_packets', 'rx_packets', 'tx_bytes', 'rx_bytes',
                           'tx_bitrate', 'rx_bitrate', 'packet_loss', 'latency_ms',
                           'throughput_kbps', 'tx_avg_packet_size', 'rx_avg_packet_size']
            # Only include columns that exist
            numeric_cols = [col for col in numeric_cols if col in df.columns]
        
        print(f"Normalizing {len(numeric_cols)} features...")
        
        # Fit scaler on training data
        if not self.scaler_fitted:
            self.scaler.fit(df[numeric_cols])
            self.scaler_fitted = True
            
            # Save scaler
            scaler_path = os.path.join(self.scaler_dir, 'num_scaler.pkl')
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            print(f"Scaler saved to {scaler_path}")
        
        # Transform
        df[numeric_cols] = self.scaler.transform(df[numeric_cols])
        
        return df
    
    def create_time_features(self, df):
        """Create time-based features"""
        print("Creating time features...")
        
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df['hour'] = df['time'].dt.hour
            df['minute'] = df['time'].dt.minute
            df['day_of_week'] = df['time'].dt.dayofweek
            
            # Cyclical encoding for time features
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['minute_sin'] = np.sin(2 * np.pi * df['minute'] / 60)
            df['minute_cos'] = np.cos(2 * np.pi * df['minute'] / 60)
            df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Create time index (integer)
        df = df.sort_values('time')
        df['time_idx'] = range(len(df))
        
        return df
    
    def create_static_features(self, df):
        """Create static features from link_id"""
        print("Creating static features...")
        
        if 'link_id' in df.columns:
            # Extract switch and port from link_id (format: s{dpid}_p{port})
            df['switch_id'] = df['link_id'].str.extract(r's(\d+)_p')
            df['port_id'] = df['link_id'].str.extract(r'_p(\d+)')
            
            # Convert to numeric
            df['switch_id'] = pd.to_numeric(df['switch_id'], errors='coerce').fillna(0)
            df['port_id'] = pd.to_numeric(df['port_id'], errors='coerce').fillna(0)
        
        return df
    
    def split_train_val(self, df, val_split=0.2):
        """
        Split data into train and validation sets (time-based, no shuffling)
        
        Args:
            df: DataFrame
            val_split: Fraction of data for validation
        """
        print(f"Splitting data: train={1-val_split:.2f}, val={val_split:.2f}")
        
        split_idx = int(len(df) * (1 - val_split))
        train_df = df.iloc[:split_idx].copy()
        val_df = df.iloc[split_idx:].copy()
        
        print(f"Train: {len(train_df)} rows, Val: {len(val_df)} rows")
        
        return train_df, val_df
    
    def process(self, save_processed=True, save_train_val=True):
        """
        Complete preprocessing pipeline
        
        Args:
            save_processed: Save processed CSV
            save_train_val: Save separate train/val CSVs
        """
        print("=== Starting Preprocessing Pipeline ===")
        
        # Load data
        df = self.load_raw_data()
        
        # Handle missing values
        df = self.handle_missing_values(df, method='forward_fill')
        
        # Handle outliers
        df = self.handle_outliers(df, method='clip')
        
        # Create time features
        df = self.create_time_features(df)
        
        # Create static features
        df = self.create_static_features(df)
        
        # Normalize features
        df = self.normalize_features(df)
        
        # Save processed data
        if save_processed:
            processed_path = os.path.join(self.processed_data_dir, 'processed.csv')
            df.to_csv(processed_path, index=False)
            print(f"Processed data saved to {processed_path}")
        
        # Split and save train/val
        if save_train_val:
            train_df, val_df = self.split_train_val(df, val_split=0.2)
            
            train_path = os.path.join(self.processed_data_dir, 'train.csv')
            val_path = os.path.join(self.processed_data_dir, 'val.csv')
            
            train_df.to_csv(train_path, index=False)
            val_df.to_csv(val_path, index=False)
            
            print(f"Train data saved to {train_path}")
            print(f"Validation data saved to {val_path}")
        
        print("=== Preprocessing Complete ===")
        return df

if __name__ == '__main__':
    preprocessor = DataPreprocessor()
    df = preprocessor.process()

