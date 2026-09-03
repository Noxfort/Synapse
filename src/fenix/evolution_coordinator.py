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
# File: src/fenix/evolution_coordinator.py
# Author: Gabriel Moraes
# Date: 2026-09-01

"""
Evolution Coordinator for F.E.N.I.X. (SOLID Architecture).
Strictly adheres to SRP by managing asynchronous Level 2 Evolution training,
callbacks wiring, and hot-swap dispatching.
"""

import threading
from typing import Optional, Callable

from src.utils.logging_setup import get_logger
from src.fenix.protocols import (
    IEvolutionCoordinator,
    IFenixStrategy,
    StrategyCallbacks,
    IDriftEvaluator,
    IMaintenanceScheduler,
)
from src.fenix.evolution_strategy import Level2EvolutionStrategy

logger = get_logger("FenixEvolutionCoordinator")


class FenixEvolutionCoordinator(IEvolutionCoordinator):
    """
    Coordinates asynchronous background model evolution cycles (Level 2 Evolution).
    Decouples ML retraining lifecycles and callback routing from process monitoring.
    """

    def __init__(
        self,
        strategy: Optional[IFenixStrategy] = None,
        drift_evaluator: Optional[IDriftEvaluator] = None,
        scheduler: Optional[IMaintenanceScheduler] = None,
        on_model_hot_swap: Optional[Callable[[str], None]] = None,
    ):
        self.strategy = strategy or Level2EvolutionStrategy()
        self.drift_evaluator = drift_evaluator
        self.scheduler = scheduler
        self.on_model_hot_swap = on_model_hot_swap

        self._is_evolving = False
        self._stop_requested = False
        self._evolution_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def is_evolving(self) -> bool:
        """Returns True if an evolution cycle is currently executing in background."""
        with self._lock:
            return self._is_evolving

    def stop(self) -> None:
        """Signals active evolution workers to interrupt cleanly."""
        self._stop_requested = True

    def trigger_evolution(
        self,
        on_complete: Optional[Callable[[bool, str], None]] = None
    ) -> bool:
        """
        Runs background Level 2 model evolution without blocking main processing.

        Args:
            on_complete: Optional callback invoked with (success, message) upon finish.

        Returns:
            bool: True if cycle was started, False if already in progress.
        """
        with self._lock:
            if self._is_evolving:
                logger.warning("[EVOLUTION COORDINATOR] Evolution cycle already in progress.")
                return False

            self._is_evolving = True
            self._stop_requested = False
            logger.info("[EVOLUTION COORDINATOR] 🦅 Initiating Level 2 Evolution in background...")

            def _evolution_worker():
                callbacks = StrategyCallbacks(
                    on_progress=lambda msg, pct: logger.info(f"[FENIX N2 EVOLUTION] ({pct}%): {msg}"),
                    on_request_fallback=lambda active: None,
                    on_request_neural_reset=lambda: None,
                    on_request_model_hot_swap=lambda path: self._dispatch_hot_swap(path),
                    is_interrupted=lambda: self._stop_requested,
                )
                try:
                    success = self.strategy.execute(callbacks)
                    if on_complete:
                        on_complete(success, "Evolution successful.")
                except Exception as e:
                    logger.error(f"[EVOLUTION COORDINATOR] Evolution failed: {e}")
                    if on_complete:
                        on_complete(False, str(e))
                finally:
                    with self._lock:
                        self._is_evolving = False

            self._evolution_thread = threading.Thread(target=_evolution_worker, daemon=True)
            self._evolution_thread.start()
            return True

    def _dispatch_hot_swap(self, model_checkpoint_path: str) -> None:
        """Dispatches hot-swap event when new model checkpoint is generated."""
        logger.info(f"[EVOLUTION COORDINATOR] 🔄 New model candidate ready: {model_checkpoint_path}")
        if self.on_model_hot_swap:
            try:
                self.on_model_hot_swap(model_checkpoint_path)
            except Exception as e:
                logger.error(f"[EVOLUTION COORDINATOR] Error in on_model_hot_swap callback: {e}")
