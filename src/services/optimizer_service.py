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
# File: src/services/optimizer_service.py
# Author: Gabriel Moraes
# Date: 2026-03-02

import os
import gc
import torch
import optuna
from typing import Optional, Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal

# --- Utils ---
from src.utils.logging_setup import logger

# --- Optimization Modules (DIP: depends on abstractions only) ---
from src.optimization.data_loader import DataLoader
from src.optimization.callbacks import DerivativeConvergenceCallback
from src.optimization.task_registry import TaskRegistry
from src.optimization.optimization_task import OptimizationTask


class OptimizerService(QObject):
    """
    Manages Hyperparameter Optimization (AutoML) using Optuna.
    
    Refactored V35 (SOLID Compliance):
    - SRP: Pure orchestrator. No data prep, no model instantiation, no I/O.
    - OCP: Iterates over a dynamic task list. New agents = new task in TaskRegistry.
    - DIP: Depends only on OptimizationTask abstraction, not concrete strategies.
    """
    
    training_finished = pyqtSignal(dict)
    optimization_finished = pyqtSignal()

    def __init__(self): 
        super().__init__()
        self.safety_max_trials = 500 
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.base_dir = os.path.join(os.path.expanduser("~"), "Documentos", "Synapse")
        self.checkpoint_dir = os.path.join(self.base_dir, "Checkpoint")
        self.checkpoint_file = os.path.join(self.checkpoint_dir, "best_hparams.pth")
        
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def run(self, map_file_path: Optional[str] = None, history_file_path: Optional[str] = None):
        """
        Main execution pipeline.
        Loads data, builds the task list, and executes each phase sequentially.
        """
        logger.info("[OptimizerService] 🧠 Starting Calculus-Based AutoML...")
        
        # 1. Initial State Check
        self._force_cleanup()

        if os.path.exists(self.checkpoint_file):
            logger.info("[OptimizerService] 💾 Checkpoint found. Skipping optimization.")
            self.optimization_finished.emit()
            return 

        # 2. Data Loading (Delegated to DataLoader)
        if not history_file_path or not os.path.exists(history_file_path):
            logger.error("[OptimizerService] ❌ CRITICAL: No User Parquet File provided.")
            raise ValueError(f"No User Parquet File provided or path does not exist: '{history_file_path}'")

        univ_data = DataLoader.load_parquet_data(history_file_path)
        if univ_data is None:
            raise RuntimeError(f"Failed to load or parse Parquet dataset from '{history_file_path}'.")

        map_graph = None
        if map_file_path and os.path.exists(map_file_path):
            map_graph = DataLoader.load_sumo_map(map_file_path)

        # 3. Build Task List (Delegated to TaskRegistry — OCP + DIP)
        tasks = TaskRegistry.build_tasks(
            univ_data=univ_data,
            map_graph=map_graph,
            map_file_path=map_file_path,
            device=self.device,
            base_dir=self.base_dir
        )

        # 4. Execute Tasks (Generic Loop — knows nothing about agents)
        final_results = {}

        for task in tasks:
            if not task.enabled:
                logger.info(f"[OptimizerService] ⏩ Skipping {task.label} (disabled)")
                continue

            logger.info(f"[OptimizerService] {task.label}...")
            
            best_params = self._optimize_phase(
                task.objective_fn,
                task.slope_threshold,
                task.window
            )
            
            final_results[task.name] = best_params

            # Execute post-optimization hook if defined (e.g., save diploma)
            if task.post_hook and best_params:
                task.post_hook(best_params)

        # 5. Save Results
        self._save_results(final_results)

    def _optimize_phase(self, objective_fn, slope_threshold=1e-5, window=25) -> Dict[str, Any]:
        """
        Generic Optimization Loop.
        Handles Study creation, Callbacks, and Resource Cleanup.
        """
        pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=2, interval_steps=1)
        study = optuna.create_study(direction="minimize", pruner=pruner)
        
        callback = DerivativeConvergenceCallback(
            slope_threshold=slope_threshold, 
            window_size=window, 
            min_trials=35,
            signal_emitter=self.training_finished.emit
        )
        
        try:
            study.optimize(objective_fn, n_trials=self.safety_max_trials, callbacks=[callback])
            best_params = study.best_params
        except Exception as e:
            logger.error(f"[OptimizerService] Phase Failed: {e}")
            best_params = {}
        
        # Cleanup
        del study
        self._force_cleanup()
        
        return best_params

    def _save_results(self, final_results: Dict[str, Any]):
        """Persists the optimization results to the checkpoint file."""
        self._force_cleanup()
        
        try:
            torch.save(final_results, self.checkpoint_file)
            logger.info("[OptimizerService] ✅✅ CHECKPOINT SAVED. Optimization Complete.")
            try:
                from src.database.db_engine import DatabaseEngine
                from src.repositories.cloud_vault_repo import CloudVaultRepository
                engine = DatabaseEngine()
                repo = CloudVaultRepository(engine)
                repo.sync_file_to_vault(self.checkpoint_file, self.base_dir)
                logger.info("[OptimizerService] ☁️ Checkpoint best_hparams.pth sincronizado no PostgreSQL Cloud Vault.")
            except Exception as dbe:
                logger.debug(f"[OptimizerService] Cloud vault sync notice: {dbe}")
            self.optimization_finished.emit()
        except Exception as e:
            logger.error(f"[OptimizerService] ❌ Failed to save checkpoint: {e}")

    def _force_cleanup(self):
        """
        Forces Python GC and PyTorch CUDA Cache to release all resources.
        Critical for avoiding OOM between sequential phases.
        """
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        logger.info("[OptimizerService] 🧹 Resources Flushed (RAM + VRAM).")
