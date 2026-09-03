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
# File: src/services/fenix_service.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import threading
from typing import Dict, Optional, Any
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

from src.utils.logging_setup import logger
from src.fenix.protocols import TriggerType, IFenixStrategy, StrategyCallbacks
from src.fenix.hot_reset_strategy import Level1HotResetStrategy
from src.fenix.evolution_strategy import Level2EvolutionStrategy
from src.fenix.maintenance_scheduler import MaintenanceScheduler
from src.fenix.drift_evaluator import DriftEvaluator


class FenixService(QObject):
    """
    F.E.N.I.X. Service (Fail-safe Evolutionary Neural Inference eXchange).
    
    PURE ORCHESTRATOR / FACADE (SOLID Aligned):
    - Acts as the central Qt-friendly facade for callers (Auditor, MainController, UI).
    - Delegates scheduling to `MaintenanceScheduler`.
    - Delegates drift/anomaly checks to `DriftEvaluator`.
    - Delegates execution workflows to `IFenixStrategy` implementations:
        * Level 1: Hot-Reset (~1-2s via Level1HotResetStrategy)
        * Level 2: Autonomous Evolution (via Level2EvolutionStrategy)
    - Emits PyQt signals on behalf of the execution lifecycle.
    """

    # --- Signals ---
    cycle_started = pyqtSignal(str)
    cycle_finished = pyqtSignal(bool, str)
    progress_update = pyqtSignal(str, int)

    # Critical System Commands
    request_fallback_activation = pyqtSignal(bool)  # Signals AFB process to activate/deactivate
    request_neural_reset = pyqtSignal()             # Signals CycleProcessor/Nodes to flush & reload weights
    request_model_hot_swap = pyqtSignal(str)

    def __init__(
        self,
        storage_manager: Optional[Any] = None,
        app_state: Optional[Any] = None,
        scheduler: Optional[MaintenanceScheduler] = None,
        drift_evaluator: Optional[DriftEvaluator] = None,
        strategies: Optional[Dict[TriggerType, IFenixStrategy]] = None
    ):
        super().__init__()
        self.storage = storage_manager
        self.app_state = app_state
        self.is_running = False
        self.stop_requested = False
        self.is_monitoring_active = False

        # Injected or default modular components (DIP / SRP)
        self.maintenance_scheduler = scheduler or MaintenanceScheduler()
        self.drift_evaluator = drift_evaluator or DriftEvaluator()

        # Strategy registry (OCP)
        self.strategies: Dict[TriggerType, IFenixStrategy] = strategies or {
            TriggerType.EMERGENCY: Level1HotResetStrategy(),
            TriggerType.OPPORTUNISTIC: Level2EvolutionStrategy(storage=self.storage)
        }

        # Worker Thread
        self.worker_thread: Optional[threading.Thread] = None

        # Scheduler Timer (Periodic check)
        self.scheduler = QTimer(self)
        self.scheduler.timeout.connect(self._check_opportunity)

        logger.info("[FENIX] Service initialized as Pure Orchestrator / Facade.")

    # --- Properties (Delegation to Subcomponents) ---
    @property
    def reconstruction_threshold(self) -> float:
        return self.drift_evaluator.reconstruction_threshold

    @reconstruction_threshold.setter
    def reconstruction_threshold(self, value: float):
        self.drift_evaluator.reconstruction_threshold = value

    @property
    def min_drift_days(self) -> int:
        return self.drift_evaluator.min_drift_days

    @min_drift_days.setter
    def min_drift_days(self, value: int):
        self.drift_evaluator.min_drift_days = value

    @property
    def schedule_path(self) -> Path:
        return self.maintenance_scheduler.schedule_path

    @schedule_path.setter
    def schedule_path(self, path: Path):
        self.maintenance_scheduler.schedule_path = path

    @property
    def schedule_map(self) -> Dict[str, int]:
        return self.maintenance_scheduler.schedule_map

    @schedule_map.setter
    def schedule_map(self, mapping: Dict[str, int]):
        self.maintenance_scheduler.schedule_map = mapping

    # --- Lifecycle & Monitoring Facade ---
    def activate_monitoring(self):
        """Called by MainController when Phase 2 (Online Operation) begins."""
        if self.is_monitoring_active:
            return

        logger.info("[FENIX] 🟢 Activating Autonomous Opportunity Scanner...")
        self.maintenance_scheduler.load_schedule()
        self.is_monitoring_active = True
        self.scheduler.start(600000)  # 10 Minutes
        QTimer.singleShot(5000, self._check_opportunity)

    def deactivate_monitoring(self):
        """Called when system stops."""
        logger.info("[FENIX] 🔴 Hibernating Opportunity Scanner.")
        self.is_monitoring_active = False
        self.scheduler.stop()

    @pyqtSlot()
    def _check_opportunity(self):
        """Autonomous Level 2 Evaluation (Valley Slot + Multi-Day Drift Gatekeeper)."""
        if not self.is_monitoring_active or self.is_running:
            return

        is_valley, slot_key = self.maintenance_scheduler.is_opportunity_slot()
        if is_valley:
            if self.drift_evaluator.has_significant_multiday_drift():
                logger.info(f"[FENIX] 🦅 Significant Multi-Day Drift detected in Valley Slot {slot_key}. Initiating Level 2 Evolution.")
                self.start_fenix_cycle(TriggerType.OPPORTUNISTIC)
            else:
                logger.info(f"[FENIX] 💤 Valley Slot {slot_key} reached, but multi-day distribution is stable. Hibernating (GPU saved).")

    def _has_significant_multiday_drift(self) -> bool:
        return self.drift_evaluator.has_significant_multiday_drift()

    @pyqtSlot(float)
    def check_health_metrics(self, current_reconstruction_error: float):
        """Checks for Critical Anomalies (Triggers Level 1 Hot-Reset)."""
        if not self.is_monitoring_active or self.is_running:
            return

        if self.drift_evaluator.is_anomaly_critical(current_reconstruction_error):
            logger.warning(
                f"[FENIX] ⚠️ EMERGENCY TRIGGER: Reconstruction Error {current_reconstruction_error:.2f} > {self.reconstruction_threshold}"
            )
            self.start_fenix_cycle(TriggerType.EMERGENCY)

    def trigger_emergency_reset(self):
        """Direct entry point for Auditor to trigger Level 1 Hot-Reset."""
        if not self.is_running:
            logger.critical("[FENIX] 🚨 Emergency Hot-Reset requested by AuditorAgent.")
            self.start_fenix_cycle(TriggerType.EMERGENCY)

    # --- Strategy Execution Engine ---
    def start_fenix_cycle(self, trigger: TriggerType):
        if self.is_running:
            return

        strategy = self.strategies.get(trigger)
        if not strategy:
            logger.error(f"[FENIX] No strategy registered for trigger: {trigger}")
            return

        self.is_running = True
        self.stop_requested = False
        self.cycle_started.emit(f"F.E.N.I.X. Cycle Initiated: {trigger.name}")

        self.worker_thread = threading.Thread(target=self._run_strategy, args=(strategy,))
        self.worker_thread.start()

    def _run_strategy(self, strategy: IFenixStrategy):
        callbacks = StrategyCallbacks(
            on_progress=self._update_status,
            on_request_fallback=self.request_fallback_activation.emit,
            on_request_neural_reset=self.request_neural_reset.emit,
            on_request_model_hot_swap=self.request_model_hot_swap.emit,
            is_interrupted=lambda: self.stop_requested
        )

        try:
            strategy.execute(callbacks)
            status_text = "Successful." if "Hot-Reset" in strategy.name else "Complete."
            self.cycle_finished.emit(True, f"{strategy.name} {status_text}")
        except Exception as e:
            err_tag = "Hot-Reset" if "Hot-Reset" in strategy.name else "Evolution"
            self.cycle_finished.emit(False, f"{err_tag} Error: {str(e)}")
        finally:
            self.is_running = False

    def stop_cycle(self):
        self.stop_requested = True

    def _update_status(self, msg: str, percent: int):
        logger.info(f"[FENIX] {msg}")
        self.progress_update.emit(msg, percent)
