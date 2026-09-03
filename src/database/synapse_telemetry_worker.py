# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# File: src/database/synapse_telemetry_worker.py
# Author: Gabriel Moraes
# Date: 2026-09-02

import time
import queue
import logging
import threading
from typing import TYPE_CHECKING, List, Dict, Any, Optional

if TYPE_CHECKING:
    from src.repositories.sensor_telemetry_writer import SensorTelemetryWriter

logger = logging.getLogger("Synapse.TelemetryWorker")


class SynapseTelemetryWorker:
    """
    Non-blocking async background worker for real-time sensor telemetry.
    Pushes telemetry into an in-memory queue in < 0.001 ms without locking
    the real-time neural inference cycle (deadline < 250ms).
    Flushes compressed delta batches to PostgreSQL in background.
    Ported and adapted from CARINA StepDecisionWorker.
    """

    def __init__(
        self,
        writer: 'SensorTelemetryWriter',
        flush_interval_sec: float = 3.0,
        batch_threshold: int = 50,
        queue_maxsize: int = 50000
    ):
        self.writer = writer
        self.flush_interval_sec = flush_interval_sec
        self.batch_threshold = batch_threshold

        self._queue: queue.Queue = queue.Queue(maxsize=queue_maxsize)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        """Starts the background telemetry flushing thread."""
        with self._lock:
            if not self._running:
                self._running = True
                self._thread = threading.Thread(
                    target=self._worker_loop,
                    daemon=True,
                    name="SynapseTelemetryWorkerThread"
                )
                self._thread.start()
                logger.info("[SynapseTelemetryWorker] Async telemetry background worker started.")

    def stop(self):
        """Stops the worker thread and flushes any pending telemetry items."""
        with self._lock:
            if self._running:
                self._running = False
                if self._thread and self._thread.is_alive():
                    self._thread.join(timeout=2.0)
                self._flush_batch(force_flush_delta=True)
                logger.info("[SynapseTelemetryWorker] Background worker stopped and flushed.")

    def push_telemetry(
        self,
        sensor_id: str,
        speed: float,
        flow_rate: float,
        occupancy: float,
        status: int = 2,
        scenario_name: str = "default",
        collected_at: Optional[Any] = None
    ) -> bool:
        """
        Ultra-fast non-blocking push (< 0.001 ms) into RAM queue.
        Safely drops oldest packet if queue fills up to avoid blocking inference loop.
        """
        packet = {
            "sensor_id": sensor_id,
            "speed": speed,
            "flow_rate": flow_rate,
            "occupancy": occupancy,
            "status": status,
            "scenario_name": scenario_name,
            "collected_at": collected_at
        }
        try:
            self._queue.put_nowait(packet)
            return True
        except queue.Full:
            try:
                # Drop one old packet to make room
                self._queue.get_nowait()
                self._queue.put_nowait(packet)
                return True
            except Exception:
                return False

    def _flush_batch(self, force_flush_delta: bool = False):
        """Drains buffered telemetry from RAM queue and passes to SensorTelemetryWriter."""
        samples: List[Dict[str, Any]] = []
        while not self._queue.empty():
            try:
                samples.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if samples or force_flush_delta:
            self.writer.insert_telemetry_batch(samples, force_flush_delta=force_flush_delta)

    def _worker_loop(self):
        """Background thread execution loop."""
        last_flush = time.time()
        while self._running:
            try:
                time.sleep(0.5)
                now = time.time()
                q_size = self._queue.qsize()
                if (now - last_flush) >= self.flush_interval_sec or q_size >= self.batch_threshold:
                    self._flush_batch()
                    last_flush = now
            except Exception as e:
                logger.error(f"[SynapseTelemetryWorker] Error in worker loop: {e}")
