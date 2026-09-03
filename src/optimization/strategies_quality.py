# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: src/optimization/strategies_quality.py
# Author: Gabriel Moraes
# Date: 2026-02-15

import torch
import torch.nn as nn
import numpy as np
import logging
from typing import Any
import optuna

# Import Agents
from src.agents.auditor_agent import AuditorAgent
from src.agents.imputer_agent import ImputerAgent
from src.agents.corrector_agent import CorrectorAgent
from src.utils.convergence_tracker import MarginalConvergenceTracker

# Logger
logger = logging.getLogger("Synapse.Strategies.Quality")

class QualityStrategies:
    """
    Optimization Strategies for Quality Assurance Agents.
    Contains logic for Auditor (Security), Imputer (Resilience), and Corrector (Denoising).
    """

    @staticmethod
    def auditor_strategy(trial, data: np.ndarray, device: torch.device) -> float:
        """
        Optimizes the Auditor Agent (Wavelet AE + PINN + OCC).
        Target: Minimize Reconstruction Loss + Compactness (One-Class) + Physics.
        """
        # 1. Hyperparameters (Stabilized Range)
        lr = trial.suggest_float("lr", 1e-5, 1e-3, log=True) # Cap at 1e-3
        latent_dim = trial.suggest_categorical("latent_dim", [8, 16])
        J = trial.suggest_int("J", 1, 2) # Keep scattering scale small for stability
        
        # 2. Data Prep
        # Auditor expects [Batch, Input_Len] (Univariate usually or flattened multivariate)
        if data.ndim > 1:
            # Flatten or select main channel. For simplicity, we take the first component
            # assuming it's the most relevant signal (e.g., flow).
            signal = data[:, 0]
        else:
            signal = data
            
        # Sliding Window
        window_size = 60 # Fixed window for Wavelet consistency
        if len(signal) > window_size:
            x_train = []
            # Create a small batch of windows
            for i in range(0, min(len(signal)-window_size, 500), window_size):
                 x_train.append(signal[i:i+window_size])
            
            if not x_train: return float('inf')
            
            x_tensor = torch.FloatTensor(np.array(x_train)).to(device)
        else:
            return float('inf')

        # 3. Instantiate Agent
        try:
            agent = AuditorAgent(
                input_len=window_size,
                J=J,
                latent_dim=latent_dim,
                learning_rate=lr
            )
            agent.to(device)
        except Exception as e:
            logger.error(f"[Auditor] Init Error: {e}")
            return float('inf')

        # 4. Dynamic Training Loop (Marginal Convergence + Pruning)
        try:
            tracker = MarginalConvergenceTracker(
                min_epochs=3,
                max_epochs=20,
                patience=3,
                min_delta=1e-4,
                optuna_trial=trial
            )
            
            # Use subset for HPO speed
            batch = x_tensor[:16] 
            
            for epoch in range(tracker.max_epochs):
                loss = agent.train_step(batch)
                
                if not np.isfinite(loss):
                    return float('inf')
                    
                if tracker.step(epoch, loss, model=agent.model):
                    break
            
            return tracker.best_loss

        except optuna.TrialPruned:
            raise
        except Exception as e:
            logger.warning(f"[Auditor] Training failed: {e}")
            return float('inf')
        finally:
            del agent
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    @staticmethod
    def imputer_strategy(trial, data: np.ndarray, device: torch.device) -> float:
        """
        Optimizes the Imputer Agent (PatchTST).
        Target: Masked Reconstruction Loss (MSE).
        """
        # 1. Hyperparameters (PatchTST)
        lr = trial.suggest_float("lr", 1e-5, 1e-3, log=True)
        d_model = trial.suggest_categorical("d_model", [32, 64, 128])
        n_heads = trial.suggest_categorical("n_heads", [2, 4])
        n_layers = trial.suggest_int("n_layers", 2, 3)
        patch_len = trial.suggest_categorical("patch_len", [4, 8, 12])
        dropout = trial.suggest_float("dropout", 0.05, 0.3)
        
        # 2. Data Prep
        seq_len = 24
        feature_dim = data.shape[1] if data.ndim > 1 else 1
        stride = max(1, patch_len // 2)
        
        if len(data) > seq_len:
            # Create batch [Batch, Seq, Feat]
            batch_data = []
            for i in range(min(10, len(data) - seq_len)):
                if data.ndim > 1:
                    batch_data.append(data[i:i + seq_len])
                else:
                    batch_data.append(data[i:i + seq_len].reshape(-1, 1))
            
            x_tensor = torch.FloatTensor(np.array(batch_data)).to(device)
        else:
            return float('inf')

        # 3. Instantiate
        try:
            agent = ImputerAgent(
                feature_dim=feature_dim,
                seq_len=seq_len,
                patch_len=patch_len,
                stride=stride,
                d_model=d_model,
                n_heads=n_heads,
                n_layers=n_layers,
                dropout=dropout,
                learning_rate=lr
            )
            agent.to(device)
        except Exception as e:
            logger.error(f"[Imputer] Init Error: {e}")
            return float('inf')

        # 4. Dynamic Training Loop (Marginal Convergence + Pruning)
        try:
            tracker = MarginalConvergenceTracker(
                min_epochs=3,
                max_epochs=20,
                patience=3,
                min_delta=1e-4,
                optuna_trial=trial
            )
            
            for epoch in range(tracker.max_epochs):
                loss = agent.train_step(x_tensor)
                
                if not np.isfinite(loss):
                    return float('inf')
                
                if tracker.step(epoch, loss, model=agent.model):
                    break
            
            return tracker.best_loss

        except optuna.TrialPruned:
            raise
        except Exception as e:
            logger.warning(f"[Imputer] Training failed: {e}")
            return float('inf')
        finally:
            del agent
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    @staticmethod
    def corrector_strategy(trial, data: np.ndarray, device: torch.device) -> float:
        """
        Optimizes the Corrector Agent (VAE-TCN + PINN).
        Target: Reconstruction Loss (MSE) + KLD + Physics.
        """
        # 1. Hyperparameters
        lr = trial.suggest_float("lr", 1e-4, 1e-3, log=True)
        latent_dim = trial.suggest_categorical("latent_dim", [8, 16])
        kernel_size = trial.suggest_int("kernel_size", 3, 5)
        
        # 2. Data Prep (Sliding Window)
        input_dim = data.shape[1] if data.ndim > 1 else 1
        window_size = 30
        
        if len(data) > window_size:
             # Create simple batch [Batch, Window, Feat]
             batch_data = []
             # Take last 32 windows
             start_idx = max(0, len(data) - window_size - 32)
             for i in range(start_idx, len(data)-window_size):
                 chunk = data[i:i+window_size]
                 if chunk.ndim == 1: chunk = chunk.reshape(-1, 1)
                 batch_data.append(chunk)
             
             x_tensor = torch.FloatTensor(np.array(batch_data)).to(device)
             # VAE-TCN expects [Batch, Channels, Length] usually, handled inside agent
        else:
            return float('inf')

        # 3. Instantiate
        try:
            agent = CorrectorAgent(
                input_dim=input_dim,
                hidden_dim=32, # Fixed for speed
                latent_dim=latent_dim,
                kernel_size=kernel_size,
                learning_rate=lr
            )
            agent.to(device)
        except Exception as e:
            logger.error(f"[Corrector] Init Error: {e}")
            return float('inf')

        # 4. Dynamic Training Loop (Marginal Convergence + Pruning)
        try:
            tracker = MarginalConvergenceTracker(
                min_epochs=3,
                max_epochs=20,
                patience=3,
                min_delta=1e-4,
                optuna_trial=trial
            )
            
            for epoch in range(tracker.max_epochs):
                loss = agent.train_step(x_tensor)
                if not np.isfinite(loss):
                    return float('inf')
                if tracker.step(epoch, loss, model=agent.model):
                    break
                
            return tracker.best_loss

        except optuna.TrialPruned:
            raise
        except Exception as e:
            logger.warning(f"[Corrector] Training failed: {e}")
            return float('inf')
        finally:
            del agent
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
