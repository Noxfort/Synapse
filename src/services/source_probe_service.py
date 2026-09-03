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
# File: src/services/source_probe_service.py
# Author: Gabriel Moraes
# Date: 2026-08-28

import threading
import requests
from datetime import datetime
from src.domain.entities import DataSource
from src.interfaces.sources import ISourceProbeService
from src.utils.logging_setup import get_logger

logger = get_logger("SourceProbeService")


class HttpSourceProbeService(ISourceProbeService):
    """
    Service responsible for lightweight, non-blocking reachability tests on registered global API endpoints.
    (SRP: Pure network diagnostic isolation).
    """

    def __init__(self, timeout_seconds: float = 3.0):
        self.timeout_seconds = timeout_seconds

    def probe(self, source: DataSource) -> None:
        """Executes a lightweight reachability test in a background thread."""
        if source.is_local:
            logger.info(
                f"📡 [Sensor Local] Configurado para '{source.name}' (ID: '{source.id}'). "
                f"Aguardando envios via POST na porta 8080 (ativo na Fase 2)."
            )
            return

        url = str(source.connection_string or "").strip()
        if not url.startswith("http"):
            return

        def _do_probe():
            try:
                start_t = datetime.now()
                resp = requests.get(url, timeout=self.timeout_seconds)
                latency_ms = (datetime.now() - start_t).total_seconds() * 1000.0
                if resp.status_code < 400:
                    logger.info(
                        f"🌐 [Probe Conexão] Sensor Global '{source.name}' ({url}) -> "
                        f"CONECTIVIDADE OK (HTTP {resp.status_code}) em {latency_ms:.0f}ms | Tamanho payload: {len(resp.content)} bytes"
                    )
                else:
                    logger.warning(
                        f"⚠️ [Probe Conexão] Sensor Global '{source.name}' ({url}) -> "
                        f"RESPOSTA COM ALERTA (HTTP {resp.status_code}) em {latency_ms:.0f}ms"
                    )
            except Exception as e:
                logger.warning(
                    f"⚠️ [Probe Conexão] Sensor Global '{source.name}' ({url}) -> "
                    f"FALHA: {e} (Verifique URL / Rede. O sensor será mantido em Quarentena para a Fase 2)"
                )

        t = threading.Thread(target=_do_probe, daemon=True, name=f"Probe-{source.id}")
        t.start()
