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
# File: src/infrastructure/hft_recovery.py
# Author: Gabriel Moraes
# Date: 2026-08-19

import asyncio
from typing import Any, Callable, Dict, Optional
from src.interfaces.transport import IHFTTransport
from src.utils.logging_setup import get_logger

logger = get_logger("HFT.Recovery")


class HFTRecoveryManager:
    """
    Manages connection resilience, scenario map caching, and auto-recovery routines.
    """

    def __init__(self, poll_interval: float = 2.0):
        self._recovery_payload: Optional[Dict[str, Any]] = None
        self.poll_interval = poll_interval

    def set_recovery_payload(self, map_data: Dict[str, Any]) -> None:
        """Caches scenario topology definition for automatic re-upload on server restart."""
        self._recovery_payload = map_data

    def get_recovery_payload(self) -> Optional[Dict[str, Any]]:
        return self._recovery_payload

    async def perform_recovery(
        self,
        transport: IHFTTransport,
        serializer: Any,
        set_system_state_cb: Callable[[str], Any]
    ) -> bool:
        """
        Executes full recovery sequence:
        1. Ping Loop: Wait until server is back online (re-establishing channel).
        2. Topology Re-Upload: Transparently re-uploads cached scenario payload.
        3. System Re-Arm: Dispatches START command.
        """
        logger.info("🩺 Polling for Server (Ping Loop)...")

        # 1. Ping Loop: Wait until server is back online
        while transport.is_running:
            try:
                await transport.start_channel()
                if await transport.ping():
                    logger.info("✅ Server is BACK online.")
                    break
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval)

        if not transport.is_running:
            return False

        # 2. Re-Upload Map transparently
        if self._recovery_payload:
            logger.info("🔄 Re-Uploading Map to new server instance...")
            try:
                proto_scenario = serializer.pack_scenario(self._recovery_payload)
                resp = await transport.load_scenario(proto_scenario)
                if not getattr(resp, "accepted", False):
                    logger.error(f"❌ Scenario rejected during recovery: {getattr(resp, 'message', '')}")
                    return False
                logger.info("✅ Scenario Upload Accepted during recovery.")
            except Exception as e:
                logger.error(f"💥 Scenario re-upload failed: {e}", exc_info=True)
                return False
        else:
            logger.warning("⚠️ No Recovery Payload! Carina might have an empty map.")
            return False

        # 3. Re-Arm System (Send START)
        logger.info("🎮 Re-Arming System...")
        try:
            return await set_system_state_cb("START")
        except Exception as e:
            logger.error(f"💥 System re-arm failed: {e}", exc_info=True)
            return False
