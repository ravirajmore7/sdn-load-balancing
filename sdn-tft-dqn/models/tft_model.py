#!/usr/bin/env python3
"""
Temporal Fusion Transformer (TFT) Model for Traffic Prediction
Uses pytorch-forecasting library for easy implementation
"""

import pandas as pd
import numpy as np
import torch
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer, QuantileLoss
from pytorch_forecasting.data import GroupNormalizer
from pytorch_lightning import Trainer, callbacks
from pytorch_lightning.loggers import TensorBoardLogger
import os
from pathlib import Path

class TFTTrafficPredictor:
    def __init__(self, data_dir='data/processed', model_dir='models', 
                 max_encoder_length=24, max_prediction_length=12,
                 hidden_size=8, attention_head_size=1, dropout=0.1,
                 learning_rate=6.6e-5, batch_size=128):
        """
        Initialize TFT model
        
        Args:
            data_dir: Directory containing processed data
            model_dir: Directory to save models
            max_encoder_length: Length of input sequence
            max_prediction_length: Length of prediction horizon
            hidden_size: Hidden size of transformer
            attention_head_size: Number of attention heads
            dropout: Dropout rate
            learning_rate: Learning rate
            batch_size: Batch size
        """
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.max_encoder_length = max_encoder_length
        self.max_prediction_length = max_prediction_length
        self.hidden_size = hidden_size
        self.attention_head_size = attention_head_size
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        
        os.makedirs(model_dir, exist_ok=True)
        os.makedirs('data/predictions', exist_ok=True)
        
        self.training = None
        self.validation = None
        self.model = None
    
    def load_data(self):
        """Load processed data"""
        train_path = os.path.join(self.data_dir, 'train.csv')
        val_path = os.path.join(self.data_dir, 'val.csv')
        
        if not os.path.exists(train_path):
            # If train/val split doesn't exist, use processed.csv
            processed_path = os.path.join(self.data_dir, 'processed.csv')
            if os.path.exists(processed_path):
                df = pd.read_csv(processed_path)
                # Split manually
                split_idx = int(len(df) * 0.8)
                train_df = df.iloc[:split_idx]
                val_df = df.iloc[split_idx:]
            else:
                raise FileNotFoundError(f"No data files found in {self.data_dir}")
        else:
            train_df = pd.read_csv(train_path)
            val_df = pd.read_csv(val_path)
        
        print(f"Train data: {len(train_df)} rows")
        print(f"Validation data: {len(val_df)} rows")
        
        return train_df, val_df
    
    def prepare_dataset(self, train_df, val_df):
        """Prepare TimeSeriesDataSet for pytorch-forecasting"""
        # Ensure time_idx exists
        if 'time_idx' not in train_df.columns:
            train_df = train_df.sort_values('time')
            train_df['time_idx'] = range(len(train_df))
            val_df = val_df.sort_values('time')
            val_df['time_idx'] = range(len(train_df), len(train_df) + len(val_df))
        
        # Ensure group_id exists (link_id)
        if 'group_id' not in train_df.columns:
            if 'link_id' in train_df.columns:
                train_df['group_id'] = train_df['link_id']
                val_df['group_id'] = val_df['link_id']
            else:
                # Create dummy group_id
                train_df['group_id'] = 'link_0'
                val_df['group_id'] = 'link_0'
        
        # Target variable (throughput or packet count)
        target_col = 'throughput_kbps'
        if target_col not in train_df.columns:
            # Fallback to packet count
            target_col = 'tx_packets'
            if target_col not in train_df.columns:
                target_col = 'tx_bytes'
        
        print(f"Using target column: {target_col}")
        
        # Static categoricals
        static_categoricals = ['group_id']
        if 'switch_id' in train_df.columns:
            static_categoricals.append('switch_id')
        
        # Time-varying known reals (features we know in advance)
        time_varying_known_reals = []
        if 'hour_sin' in train_df.columns:
            time_varying_known_reals.extend(['hour_sin', 'hour_cos', 'minute_sin', 'minute_cos'])
        
        # Time-varying unknown reals (features we need to predict)
        time_varying_unknown_reals = [
            'tx_packets', 'rx_packets', 'tx_bytes', 'rx_bytes',
            'tx_bitrate', 'rx_bitrate', 'packet_loss', 'latency_ms'
        ]
        # Only include columns that exist
        time_varying_unknown_reals = [col for col in time_varying_unknown_reals 
                                      if col in train_df.columns]
        
        # Create training dataset
        self.training = TimeSeriesDataSet(
            train_df,
            time_idx="time_idx",
            target=target_col,
            group_ids=["group_id"],
            min_encoder_length=self.max_encoder_length // 2,
            max_encoder_length=self.max_encoder_length,
            min_prediction_length=1,
            max_prediction_length=self.max_prediction_length,
            static_categoricals=static_categoricals,
            time_varying_known_reals=time_varying_known_reals,
            time_varying_unknown_reals=time_varying_unknown_reals,
            target_normalizer=GroupNormalizer(groups=["group_id"], transformation="softplus"),
            add_relative_time_idx=True,
            add_target_scales=True,
            allow_missing_timesteps=True
        )
        
        # Create validation dataset
        self.validation = TimeSeriesDataSet.from_dataset(
            self.training, val_df, predict=True, stop_randomization=True
        )
        
        print("Datasets created successfully")
        return self.training, self.validation
    
    def create_model(self):
        """Create TFT model"""
        if self.training is None:
            raise ValueError("Must prepare dataset first")
        
        self.model = TemporalFusionTransformer.from_dataset(
            self.training,
            learning_rate=self.learning_rate,
            hidden_size=self.hidden_size,
            attention_head_size=self.attention_head_size,
            dropout=self.dropout,
            hidden_continuous_size=self.hidden_size,
            output_size=7,  # 7 quantiles by default
            loss=QuantileLoss(),
            log_interval=10,
            reduce_on_plateau_patience=4,
        )
        
        print("TFT model created")
        return self.model
    
    def train(self, max_epochs=50, gpus=0):
        """Train the model"""
        if self.model is None:
            self.create_model()
        
        # Create data loaders
        train_dataloader = self.training.to_dataloader(train=True, batch_size=self.batch_size, num_workers=0)
        val_dataloader = self.validation.to_dataloader(train=False, batch_size=self.batch_size * 10, num_workers=0)
        
        # Setup trainer
        logger = TensorBoardLogger("lightning_logs")
        
        early_stop_callback = callbacks.EarlyStopping(
            monitor="val_loss", min_delta=1e-4, patience=10, verbose=False, mode="min"
        )
        
        trainer = Trainer(
            max_epochs=max_epochs,
            gpus=gpus,
            enable_model_summary=True,
            gradient_clip_val=0.1,
            callbacks=[early_stop_callback],
            logger=logger,
        )
        
        print("Starting training...")
        trainer.fit(
            self.model,
            train_dataloaders=train_dataloader,
            val_dataloaders=val_dataloader,
        )
        
        # Save model
        model_path = os.path.join(self.model_dir, 'tft.ckpt')
        trainer.save_checkpoint(model_path)
        print(f"Model saved to {model_path}")
        
        return trainer
    
    def predict(self, data=None, save_predictions=True):
        """Generate predictions"""
        if self.model is None:
            # Load saved model
            model_path = os.path.join(self.model_dir, 'tft.ckpt')
            if os.path.exists(model_path):
                self.model = TemporalFusionTransformer.load_from_checkpoint(model_path)
            else:
                raise ValueError("Model not trained or checkpoint not found")
        
        if data is None:
            # Use validation data
            if self.validation is None:
                train_df, val_df = self.load_data()
                self.prepare_dataset(train_df, val_df)
            data = self.validation
        
        # Generate predictions
        predictions = self.model.predict(data.to_dataloader(train=False, batch_size=self.batch_size * 10, num_workers=0))
        
        # Convert to DataFrame
        if isinstance(predictions, torch.Tensor):
            predictions = predictions.cpu().numpy()
        
        # Get actual values for comparison
        actuals = torch.cat([y for x, (y, weight) in iter(data.to_dataloader(train=False, batch_size=self.batch_size * 10, num_workers=0))], dim=0)
        actuals = actuals.cpu().numpy()
        
        # Create prediction DataFrame
        pred_df = pd.DataFrame({
            'link_id': data.data['group_id'].values[:len(predictions)],
            'time_idx': data.data['time_idx'].values[:len(predictions)],
            'actual': actuals.flatten()[:len(predictions)],
            'predicted': predictions.flatten()[:len(predictions)],
        })
        
        # Add forecasted values for next steps
        for step in range(1, self.max_prediction_length):
            if step < len(predictions[0]) if len(predictions.shape) > 1 else 1:
                pred_df[f'forecast_t+{step}'] = predictions[:, step] if len(predictions.shape) > 1 else predictions
        
        if save_predictions:
            pred_path = os.path.join('data/predictions', 'tft_forecast.csv')
            pred_df.to_csv(pred_path, index=False)
            print(f"Predictions saved to {pred_path}")
        
        return pred_df

if __name__ == '__main__':
    # Initialize and train
    predictor = TFTTrafficPredictor()
    
    # Load data
    train_df, val_df = predictor.load_data()
    
    # Prepare datasets
    predictor.prepare_dataset(train_df, val_df)
    
    # Create and train model
    predictor.create_model()
    predictor.train(max_epochs=50)
    
    # Generate predictions
    predictions = predictor.predict()
    print("Training and prediction complete!")

