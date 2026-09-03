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
# File: src/adapters/http_poller_adapter.py
# Author: Gabriel Moraes
# Date: 2026-08-29

from concurrent.futures import ThreadPoolExecutor
import time
from typing import Any, Dict, Optional
import requests

from src.domain.entities import DataSource, SourceStatus
from src.adapters.base_adapter import BaseIngestionAdapter


class HttpPollerAdapter(BaseIngestionAdapter):
    """
    HTTP PULL / Poller Ingestion Adapter.
    Actively queries external REST APIs (e.g. Waze, TomTom, OpenData, remote camera endpoints).
    Features adaptive polling rates (rapid cadence in Quarantine, normal cadence when Active).
    """

    def __init__(
        self,
        adapter_id: str = "http_poller_global",
        max_workers: int = 4,
        fast_poll_interval: float = 10.0,
        normal_poll_interval: float = 300.0,
        timeout: float = 10.0,
    ):
        super().__init__(adapter_id=adapter_id, transport_name="HTTP-Poller")
        self.max_workers = max_workers
        self.fast_poll_interval = fast_poll_interval
        self.normal_poll_interval = normal_poll_interval
        self.timeout = timeout

        self._executor: Optional[ThreadPoolExecutor] = None
        self._sources: Dict[str, DataSource] = {}
        self._last_fetch_per_source: Dict[str, float] = {}

    def _do_start(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        # Immediate initial poll across registered sources
        now = time.time()
        self.check_poll(now, force=True)

    def _do_stop(self) -> None:
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def register_source(self, source: DataSource) -> None:
        """Registers an external API source to be polled."""
        if not source.is_local and source.connection_string and isinstance(source.connection_string, str):
            if source.connection_string.startswith("http://") or source.connection_string.startswith("https://"):
                is_new = (source.id not in self._sources) or (self._sources[source.id].connection_string != source.connection_string)
                self._sources[source.id] = source
                if is_new:
                    self._logger.info(f"🌐 [HttpPollerAdapter] Registered global source '{source.name}' ({source.id}) -> {source.connection_string}")

    def unregister_source(self, source_id: str) -> None:
        if source_id in self._sources:
            del self._sources[source_id]
        if source_id in self._last_fetch_per_source:
            del self._last_fetch_per_source[source_id]

    def check_poll(self, current_time: float, force: bool = False) -> None:
        """Evaluates per-source adaptive intervals and schedules fetch jobs."""
        if not self.is_running or not self._executor:
            return

        for source_id, src in list(self._sources.items()):
            is_quarantine = (src.status == SourceStatus.QUARANTINE)
            interval = self.fast_poll_interval if is_quarantine else self.normal_poll_interval

            last_time = self._last_fetch_per_source.get(source_id, 0.0)
            if force or (current_time - last_time >= interval):
                cadence_desc = f"{interval:.0f}s ({'Quarentena' if is_quarantine else 'Operação'})"
                self._logger.info(f"☁️ [HttpPollerAdapter] Polling '{src.name}' ({source_id}) [cadence={cadence_desc}]...")
                self._last_fetch_per_source[source_id] = current_time
                self._executor.submit(self._fetch_url, source_id, src.connection_string)

    def _fetch_url(self, source_id: str, url: str) -> None:
        """Fetches data from remote HTTP endpoint in a background worker thread."""
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                payload: Any = {}
                try:
                    payload = response.json()
                except Exception:
                    text_data = response.text.strip()
                    if ',' in text_data or '\n' in text_data:
                        payload = {"raw_csv": text_data}
                        parts = text_data.split(',')
                        for p in parts:
                            if '=' in p:
                                k, v = p.split('=', 1)
                                payload[k.strip()] = v.strip()
                    else:
                        payload = {"value": text_data}

                if isinstance(payload, dict) and 'source_id' not in payload:
                    payload['source_id'] = source_id

                self._logger.info(
                    f"📥 [HttpPollerAdapter] Resposta recebida de '{source_id}' ({url}) | "
                    f"HTTP 200 OK | Tamanho: {len(response.content)} bytes"
                )

                self.emit_packet(
                    source_id=source_id,
                    payload=payload,
                    metadata={
                        "transport": "HTTP-Poller",
                        "url": url,
                        "status_code": response.status_code,
                    },
                )
            else:
                self._logger.warning(
                    f"❌ [HttpPollerAdapter] Falha ao consultar '{source_id}' ({url}): HTTP {response.status_code}"
                )
        except Exception as e:
            self._logger.error(f"❌ [HttpPollerAdapter] Erro de conexão ao consultar '{source_id}' ({url}): {e}")
