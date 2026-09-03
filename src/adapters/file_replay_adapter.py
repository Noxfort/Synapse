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
# File: src/adapters/file_replay_adapter.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import csv
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

from src.domain.entities import DataSource
from src.adapters.base_adapter import BaseIngestionAdapter


class FileReplayAdapter(BaseIngestionAdapter):
    """
    File / Dataset Replay Ingestion Adapter.
    Plays back historical dataset files (CSV, JSON) packet-by-packet into the pipeline,
    allowing offline evaluation, regression testing, and calibration without live hardware.
    """

    def __init__(
        self,
        adapter_id: str = "file_replay_adapter",
        file_path: Optional[str] = None,
        source_id: Optional[str] = None,
        playback_interval: float = 1.0,
        loop: bool = False,
        auto_play: bool = False,
    ):
        super().__init__(adapter_id=adapter_id, transport_name="FileReplay")
        self.file_path = file_path
        self.source_id = source_id or "replay_sensor"
        self.playback_interval = playback_interval
        self.loop = loop
        self.auto_play = auto_play

        self._records: List[Any] = []
        self._playback_cursor: int = 0
        self._thread: Optional[threading.Thread] = None

    def load_dataset(self, records: List[Any], source_id: Optional[str] = None) -> None:
        """Manually loads in-memory records to replay."""
        self._records = list(records)
        self._playback_cursor = 0
        if source_id:
            self.source_id = source_id

    def load_file(self, file_path: str, source_id: Optional[str] = None) -> None:
        """Reads CSV or JSON file from disk for replay."""
        self.file_path = file_path
        self._playback_cursor = 0
        if source_id:
            self.source_id = source_id

        if not os.path.exists(file_path):
            self._logger.warning(f"FileReplayAdapter: File not found: {file_path}")
            return

        self._records = []
        if file_path.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._records = data
                else:
                    self._records = [data]
        elif file_path.endswith(".csv"):
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self._records = list(reader)

    def _do_start(self) -> None:
        if self.file_path and not self._records:
            self.load_file(self.file_path, self.source_id)

        if self.auto_play and self._records:
            self._thread = threading.Thread(
                target=self._replay_loop,
                name=f"FileReplay-{self._adapter_id}",
                daemon=True,
            )
            self._thread.start()

    def _do_stop(self) -> None:
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
            self._thread = None

    def step(self) -> Optional[Any]:
        """Manually steps one record forward in the replay sequence."""
        if not self._records or self._playback_cursor >= len(self._records):
            return None
        record = self._records[self._playback_cursor]
        self._playback_cursor += 1
        self.emit_packet(
            source_id=self.source_id,
            payload=record,
            metadata={"transport": "FileReplay", "source_id": self.source_id, "cursor": self._playback_cursor},
        )
        return record

    def _replay_loop(self) -> None:
        """Background thread executing scheduled dataset playback."""
        idx = self._playback_cursor
        while self.is_running and idx < len(self._records):
            record = self._records[idx]
            self.emit_packet(
                source_id=self.source_id,
                payload=record,
                metadata={"transport": "FileReplay", "index": idx},
            )
            idx += 1
            self._playback_cursor = idx
            if self.loop and idx >= len(self._records):
                idx = 0
                self._playback_cursor = 0
            time.sleep(self.playback_interval)
