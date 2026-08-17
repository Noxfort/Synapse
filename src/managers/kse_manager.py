# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2025 Noxfort Systems
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
# File: src/managers/kse_manager.py
# Author: Gabriel Moraes
# Date: 2026-02-13

import time
import traceback
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, Qt

from src.domain.app_state import AppState
from src.domain.entities import SourceType, SourceStatus
from src.services.historical_manager import HistoricalManager
from src.kse.meh_bridge import MEHBridge
from src.kse.packet_builder import PacketBuilder


class KSEManager(QObject):
    """
    Kalman State Estimation (KSE) Manager - The Physics Engine Orchestrator.
    
    V43 (SOLID Refactor):
    - Pure Orchestrator: coordinates MEHBridge, PacketBuilder, and Elastic Window.
    - Delegates MEH data fetching to MEHBridge (SRP).
    - Delegates packet formatting/validation to PacketBuilder (SRP).
    - Owns only: state tracking, timing logic, and signal wiring.
    - Enforces Transmission Gate: requires at least 1 validated LOCAL sensor
      and 1 validated GLOBAL sensor before streaming to CARINA.
    """

    # Output: The physics packet ready for HFT transmission
    data_ready_for_transmission = pyqtSignal(dict)
    
    # Telemetry
    log_message = pyqtSignal(str)
    mode_changed = pyqtSignal(str)  # "REALTIME" or "HISTORICAL"

    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        
        # --- Injected Dependencies ---
        self._historical_manager = HistoricalManager(app_state)
        self._meh_bridge = MEHBridge(self._historical_manager)
        
        # --- State ---
        self.running = False
        self.current_mode = "REALTIME"
        
        # --- Timing ---
        self.last_sensor_update_time = 0.0
        self.last_transmission_time = 0.0
        self.has_new_processed_data = False
        
        # --- Data ---
        self.last_known_state = {}
        self._has_valid_data = False  # Gate: only transmits when True
        
        # --- Transmission Gate (Local + Global Validation Required) ---
        self.is_warmup_complete = False
        self._rejection_warned = False
        
        # --- Elastic Window Parameters ---
        self.min_window_ms = 0.150  # 150ms
        self.sensor_timeout_threshold = 0.5  # 0.5s without data -> HISTORICAL
        
        # --- Monitor Timer (10ms resolution) ---
        self.monitor = QTimer(self)
        self.monitor.setTimerType(Qt.TimerType.PreciseTimer)
        self.monitor.timeout.connect(self._check_elastic_window)

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    def start(self):
        if self.running:
            return
        self.running = True
        self.last_transmission_time = time.time()
        self.is_warmup_complete = False
        self._has_valid_data = False
        self._rejection_warned = False
        
        # CRITICAL: Load MEH baseline into RAM. Never operate blind.
        self._activate_meh_baseline()
        
        self.monitor.start(10)

    def stop(self):
        self.running = False
        self.monitor.stop()
        self.is_warmup_complete = False
        self._has_valid_data = False
        self._rejection_warned = False
        self.log_message.emit("[KSE] Physics Engine Stopped.")

    # =========================================================================
    # MEH ACTIVATION
    # =========================================================================

    def _activate_meh_baseline(self):
        """Loads MEH data into RAM as the initial operational baseline without transmitting prematurely."""
        meh_data = self._meh_bridge.load_baseline()
        
        if meh_data:
            self.last_known_state = meh_data
            self.has_new_processed_data = True
            self.current_mode = "HISTORICAL"
            self.mode_changed.emit("HISTORICAL")
            self.log_message.emit(
                f"[KSE] ⚡ Baseline MEH carregada na RAM ({len(meh_data)} edges). "
                f"Aguardando validação de pelo menos 1 sensor LOCAL e 1 sensor GLOBAL antes de iniciar transmissão para a CARINA."
            )
        else:
            self.log_message.emit(
                "[KSE] ⚠️ Physics Engine Started. MEH empty. Aguardando validação de sensores..."
            )

    # =========================================================================
    # CARINA TRANSMISSION GATE
    # =========================================================================

    def _check_carina_transmission_gate(self) -> bool:
        """
        Evaluates whether transmission to CARINA is authorized.
        Requires at least 1 validated LOCAL sensor AND at least 1 validated GLOBAL sensor (ACTIVE).
        """
        if self.is_warmup_complete:
            return True

        if not hasattr(self.app_state, 'get_all_data_sources'):
            return False

        all_sources = self.app_state.get_all_data_sources()
        live_sources = [
            s for s in all_sources
            if s.source_type != SourceType.SUMO_NET_XML
            and not (isinstance(s.connection_string, str) and s.connection_string.endswith(".parquet"))
            and "Historical Base" not in s.name
        ]

        active_locals = [s for s in live_sources if s.is_local and s.status == SourceStatus.ACTIVE]
        active_globals = [s for s in live_sources if not s.is_local and s.status == SourceStatus.ACTIVE]

        if active_locals and active_globals:
            self.is_warmup_complete = True
            self._has_valid_data = True
            local_names = ", ".join(s.name for s in active_locals)
            global_names = ", ".join(s.name for s in active_globals)
            self.log_message.emit(
                f"[KSE] 🚀 Transmissão para CARINA liberada! "
                f"Sensores ativos validados: LOCAL ({local_names}) | GLOBAL ({global_names})."
            )
            return True

        # Check if all local or all global sensors were rejected
        non_rejected_locals = [s for s in live_sources if s.is_local and s.status != SourceStatus.REJECTED]
        non_rejected_globals = [s for s in live_sources if not s.is_local and s.status != SourceStatus.REJECTED]

        if live_sources and (not non_rejected_locals or not non_rejected_globals):
            if not getattr(self, "_rejection_warned", False):
                self._rejection_warned = True
                missing_type = "LOCAL" if not non_rejected_locals else "GLOBAL"
                self.log_message.emit(
                    f"[KSE] ⛔ Transmissão para CARINA bloqueada: Nenhum sensor {missing_type} válido restante após descarte."
                )

        return False

    # =========================================================================
    # SENSOR INPUT
    # =========================================================================

    @pyqtSlot(dict)
    def sync_with_reality(self, sensor_snapshot: dict):
        """
        Called when InferenceEngine completes processing a frame.
        Takes over from MEH seamlessly when real data arrives and checks the Local + Global gate.
        """
        self.last_sensor_update_time = time.time()
        self.last_known_state = sensor_snapshot
        self.has_new_processed_data = True

        # Evaluate transmission gate
        self._check_carina_transmission_gate()
        
        if self.is_warmup_complete and sensor_snapshot:
            self._has_valid_data = True
        
        if self.running:
            self._check_elastic_window()

        # Transition: HISTORICAL -> REALTIME (Only once gate is satisfied)
        if self.is_warmup_complete and self.current_mode != "REALTIME":
            self.current_mode = "REALTIME"
            self._meh_bridge.deactivate()
            self.mode_changed.emit("REALTIME")
            self.log_message.emit("[KSE] 🟢 Sensor signal restored. Mode: REALTIME.")

    # =========================================================================
    # ELASTIC WINDOW (Core Timing Logic)
    # =========================================================================

    @pyqtSlot()
    def _check_elastic_window(self):
        """
        The core timing logic. Runs every 10ms.
        
        Responsibilities:
        - Enforce transmission gate (requires at least 1 local and 1 global active).
        - Refresh MEH data when in HISTORICAL mode.
        - Enforce transmission gate (no empty packets).
        - Apply elastic window timing (150ms minimum interval).
        - Delegate packet building to PacketBuilder.
        """
        if not self.running:
            return

        # --- CARINA TRANSMISSION GATE ---
        if not self._check_carina_transmission_gate():
            return

        try:
            now = time.time()
            dt_transmission = now - self.last_transmission_time
            dt_sensor = now - self.last_sensor_update_time

            # --- MEH REFRESH (Historical mode: re-query every 1s) ---
            if self.current_mode == "HISTORICAL":
                fresh_data = self._meh_bridge.refresh_if_needed()
                if fresh_data:
                    self.last_known_state = fresh_data
                    self.has_new_processed_data = True

            # --- TRANSMISSION GATE ---
            if not self._has_valid_data:
                return

            # --- ELASTIC WINDOW ---
            if dt_transmission < self.min_window_ms:
                return  # Too early

            if self.has_new_processed_data:
                packet_source = self.current_mode.lower()
                payload_data = self.last_known_state
            else:
                packet_source = "kse_dead_reckoning"
                payload_data = PacketBuilder.extrapolate(
                    self.last_known_state, dt_transmission
                )

            # --- MODE TRACKING ---
            if dt_sensor > self.sensor_timeout_threshold:
                if self.current_mode == "REALTIME":
                    self.current_mode = "HISTORICAL"
                    self._meh_bridge.is_active = True
                    self.mode_changed.emit("HISTORICAL")
                    self.log_message.emit(
                        f"[KSE] ⚠️ Signal Lost ({dt_sensor:.1f}s). "
                        f"Mode: HISTORICAL. MEH fallback active."
                    )

            # --- BUILD & TRANSMIT ---
            packet = PacketBuilder.build(payload_data, packet_source)
            if packet:
                self.data_ready_for_transmission.emit(packet)
            
            # Reset
            self.last_transmission_time = time.time()
            self.has_new_processed_data = False

        except Exception as e:
            self.log_message.emit(f"[KSE] ❌ Monitor Error: {e}")
            traceback.print_exc()