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
# File: src/workers/async_agents.py
# Author: Gabriel Moraes
# Date: 2025-12-23

import torch
import queue
import time
from PyQt6.QtCore import QThread, pyqtSignal

# Import the specific Agents
from src.agents.auditor_agent import AuditorAgent
from src.agents.linguist_agent import LinguistAgent
from src.utils.logging_setup import get_logger

logger = get_logger("AsyncWorkers")


class AuditorWorker(QThread):
    """
    Asynchronous Worker for the Auditor Agent ('O Segurança').
    
    Updated: Now returns the state_vector in the signal so the Engine 
    can forward it to XAI/Logging services if a veto occurs.
    """
    
    # Signal: (is_safe, error, threshold, state_vector)
    # Uses 'object' type for the vector to support List, Numpy or Tensor
    audit_finished = pyqtSignal(bool, float, float, object)

    def __init__(self, input_dim: int):
        super().__init__()
        self.input_dim = input_dim
        self.agent = None 
        self.data_queue = queue.Queue()
        self.is_running = True

    def submit_state(self, state_vector):
        self.data_queue.put(state_vector)

    def run(self):
        logger.info("AuditorWorker thread started.")
        try:
            self.agent = AuditorAgent(input_dim=self.input_dim)
        except Exception as e:
            logger.error(f"AuditorWorker init error: {e}", exc_info=True)
            return
        
        while self.is_running:
            try:
                state_vector = self.data_queue.get(timeout=1.0)
                
                # Perform the audit (inference)
                is_safe, error, thresh = self.agent.audit_state(state_vector)
                
                # Emit result + the vector that caused it
                self.audit_finished.emit(is_safe, error, thresh, state_vector)
                
                self.data_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"AuditorWorker runtime error: {e}", exc_info=True)

    def stop(self):
        self.is_running = False
        self.wait()


class LinguistWorker(QThread):
    """
    Asynchronous Worker for the Linguist Agent ('O Linguista').
    Updated with Explicit Type Casting and Neuro-Symbolic Progress Tracking.
    """
    
    # Signal: (column_name, inferred_type, confidence)
    analysis_finished = pyqtSignal(str, str, float)

    def __init__(self):
        super().__init__()
        self.agent = None
        self.data_queue = queue.Queue()
        self.is_running = True

    def submit_column(self, header_name: str, data_sample: list):
        """Entry point to request semantic analysis."""
        self.data_queue.put((header_name, data_sample))

    def run(self):
        logger.info("LinguistWorker thread started (Loading Transformers...).")
        
        try:
            # Initialize the heavy Linguist Agent (DistilRoBERTa)
            self.agent = LinguistAgent()
            logger.info("LinguistWorker: Neuro-Symbolic Brain Ready.")
        except Exception as e:
            logger.critical(f"LinguistWorker: Failed to load AI models: {e}", exc_info=True)
            return
        
        while self.is_running:
            try:
                # Get data
                item = self.data_queue.get(timeout=1.0)
                header_name, data_sample = item
                
                # --- Neuro-Symbolic Sample Counter ---
                current_samples = len(data_sample)
                required_samples = 60 # Default for Physical Brain
                
                # Try to fetch dynamic requirement from agent if available
                if hasattr(self.agent, 'physical_brain') and hasattr(self.agent.physical_brain, 'input_len'):
                    required_samples = self.agent.physical_brain.input_len

                logger.debug(f"LinguistWorker task for '{header_name}' (Sampler: {current_samples}/{required_samples})")

                # --- Perform Analysis ---
                try:
                    start_t = time.time()
                    result = self.agent.analyze_column(header_name, data_sample)
                    duration = time.time() - start_t
                    
                    # EXPLICIT CASTING (Crucial Fix)
                    # Ensure these are Python primitives, not numpy types
                    inf_type = str(result['inferred_type'])
                    conf = float(result['confidence'])
                    clean_name = str(header_name)
                    
                    # Extract Details for Reporting
                    details = result.get('details', {})
                    phys_score = details.get('physical_consistency', 0.0)
                    
                    # --- Understanding Verdict ---
                    understanding_status = "UNKNOWN"
                    if conf >= 0.7:
                        understanding_status = "✅ UNDERSTOOD"
                    elif conf >= 0.4:
                        understanding_status = "⚠️ PARTIALLY UNDERSTOOD"
                    else:
                        understanding_status = "❌ NOT UNDERSTOOD"

                    # Log physical check status
                    phys_msg = f"Phys-Score: {phys_score:.2f}"
                    if current_samples < required_samples:
                        phys_msg = "Physical Brain Skipped (Insuff. Data)"

                    logger.info(f"Linguist [{clean_name}] -> {understanding_status} | Type: {inf_type} ({conf*100:.1f}%) | {phys_msg} in {duration:.2f}s")

                    # Emit Result
                    self.analysis_finished.emit(clean_name, inf_type, conf)

                except Exception as e:
                    logger.error(f"Linguist analysis failed for '{header_name}': {e}", exc_info=True)
                    # Emit failure
                    self.analysis_finished.emit(str(header_name), "error", 0.0)
                
                self.data_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"LinguistWorker system error: {e}", exc_info=True)

    def stop(self):
        self.is_running = False
        self.wait()
