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
# File: src/kse/packet_builder.py
# Author: Gabriel Moraes
# Date: 2026-04-26

import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.utils.debug_logger import carina_logger


class PacketBuilder:
    """
    Single Responsibility: Build and validate HFT transmission packets.
    
    Handles:
    - Converting raw edge state dicts into the strict HFT schema.
    - Validating that packets contain real data (transmission gate).
    - Debug logging of packet construction.
    
    Does NOT handle: timing, transmission signals, or physics.
    """

    @staticmethod
    def build(data: Dict[str, Any], source: str) -> Optional[dict]:
        """
        Formats raw edge data into a strict HFT packet.
        
        Args:
            data: Dict mapping edge_id -> {density, speed, queue, ...}
            source: Origin label ("realtime", "historical", "kse_dead_reckoning")
            
        Returns:
            Formatted packet dict, or None if data is empty (gate).
        """
        # --- GATE #1: Empty data dict ---
        if not data:
            return None

        _build_start = time.time()
        _ts_start = datetime.now().strftime('%H:%M:%S.%f')[:-3]

        traffic_list = []
        for source_id, metrics in data.items():
            if "density" in metrics or "speed" in metrics:
                # Data from Historical DB / MEH (already Edge formatted)
                traffic_list.append({
                    "edge_id": str(source_id),
                    "density": float(metrics.get("density", 0.0)),
                    "speed": float(metrics.get("speed", 0.0)),
                    "queue": float(metrics.get("queue", 0.0))
                })
            else:
                # Data from Neural Pipeline (Node formatted)
                speed = 40.0
                if "physics" in metrics:
                    speed = float(metrics["physics"].get("v", 40.0))

                traffic_list.append({
                    "edge_id": str(source_id),
                    "density": float(metrics.get("value", 10.0)),
                    "speed": speed,
                    "queue": 0.0
                })

        # --- GATE #2: No edges after processing ---
        if not traffic_list:
            return None

        packet = {
            "timestamp": time.time(),
            "source": source,
            "traffic": traffic_list
        }

        # --- Debug Log ---
        _build_end = time.time()
        _ts_end = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        carina_logger.info(
            f"KSE_BUILD | mode={source} | edges={len(traffic_list)} "
            f"| start={_ts_start} | end={_ts_end} "
            f"| build_time={(_build_end - _build_start)*1000:.2f}ms"
        )

        return packet

    @staticmethod
    def extrapolate(base_state: dict, dt: float) -> dict:
        """
        Projects traffic metrics forward using KSE physics velocities.
        Used for dead reckoning when the neural engine is slow.
        
        Args:
            base_state: Last known state dict.
            dt: Time delta in seconds since last transmission.
            
        Returns:
            Extrapolated state dict.
        """
        extrapolated = {}
        for source_id, metrics in base_state.items():
            new_metrics = dict(metrics)

            if "physics" in metrics:
                v = metrics["physics"].get("v", 0.0)
                new_metrics["value"] = max(0.0, metrics.get("value", 0.0) + (v * dt))

            extrapolated[source_id] = new_metrics

        return extrapolated
