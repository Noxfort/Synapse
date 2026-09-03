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

from src.utils.debug_logger import carina_logger, carina_input_logger, carina_output_logger


class PacketBuilder:
    """
    Single Responsibility: Build and validate HFT transmission packets.
    
    Handles:
    - Converting raw edge state dicts into the strict HFT schema.
    - Validating that packets contain real data (transmission gate).
    - Debug logging of packet construction (text log + JSONL input/output dumps).
    
    Does NOT handle: timing, transmission signals, or physics.
    """

    @staticmethod
    def build(data: Dict[str, Any], source: str, app_state: Optional[Any] = None) -> Optional[dict]:
        """
        Formats raw edge/node data into a strict HFT packet covering all network edges (streets).
        
        Args:
            data: Dict mapping edge_id or node_id -> {density, speed, queue, ...}
            source: Origin label ("realtime", "historical", "kse_dead_reckoning")
            app_state: Optional AppState reference to map all SUMO edges/streets
            
        Returns:
            Formatted packet dict, or None if data is empty (gate).
        """
        # --- GATE #1: Empty data dict ---
        if not data:
            return None

        _build_start = time.time()
        _ts_start = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        _iso_start = datetime.now().isoformat()

        # Log Raw Input to JSONL dump
        try:
            carina_input_logger.log({
                "timestamp": _build_start,
                "iso_time": _iso_start,
                "source": source,
                "total_inputs": len(data),
                "data": data
            })
        except Exception:
            pass

        traffic_list = []
        
        # Traffic Physics Constants (HCM / ITS Standard)
        K_JAM = 125.0          # Maximum jam density per lane (veh/km/lane)
        VEH_EFFECTIVE_LEN = 7.5 # Average vehicle length + safety headway (meters)


        all_edges = []
        if app_state is not None:
            if hasattr(app_state, "get_all_edges"):
                all_edges = app_state.get_all_edges() or []
            elif hasattr(app_state, "topology") and hasattr(app_state.topology, "get_all_edges"):
                all_edges = app_state.topology.get_all_edges() or []

        if all_edges:
            for edge in all_edges:
                edge_id = str(edge.id)
                edge_len = getattr(edge, "length", 100.0)
                edge_lanes = getattr(edge, "lanes", 1)
                v_free = getattr(edge, "max_speed", 13.89) # Speed limit in m/s (~50 km/h)
                
                # Physical storage capacity of this specific street (max vehicles)
                max_capacity = max(1, int((edge_len / VEH_EFFECTIVE_LEN) * edge_lanes))
                
                density = 15.0 # Baseline flow (veh/km/lane)
                speed = v_free
                queue = 0
                
                if edge_id in data:
                    metrics = data[edge_id]
                    raw_d = float(metrics.get("density", metrics.get("value", 15.0)))
                    raw_s = float(metrics.get("speed", v_free))
                    
                    # Convert speed km/h to m/s if necessary
                    if raw_s > 35.0:
                        speed = raw_s / 3.6
                    else:
                        speed = raw_s
                        
                    # Handle raw volume/flow (veh/h) scaling into density (veh/km/lane)
                    if raw_d > K_JAM:
                        density = min(K_JAM, max(5.0, raw_d / 20.0))
                    else:
                        density = raw_d
                    
                    if "physics" in metrics:
                        v_phys = float(metrics["physics"].get("v", 0.0))
                        if v_phys > 0.5:
                            speed = v_phys if v_phys <= 35.0 else v_phys / 3.6
                else:
                    # Spatial Graph Interpolation: propagate hydrodynamics from connected nodes
                    node_from = data.get(edge.from_node, {}) if edge.from_node else {}
                    node_to = data.get(edge.to_node, {}) if edge.to_node else {}
                    
                    vals = []
                    speeds = []
                    if node_from:
                        v_f = float(node_from.get("value", 0.0))
                        if v_f > 0.0: vals.append(v_f)
                        spd_f = float(node_from.get("physics", {}).get("v", 0.0))
                        if spd_f > 0.5: speeds.append(spd_f)
                        
                    if node_to:
                        v_t = float(node_to.get("value", 0.0))
                        if v_t > 0.0: vals.append(v_t)
                        spd_t = float(node_to.get("physics", {}).get("v", 0.0))
                        if spd_t > 0.5: speeds.append(spd_t)
                        
                    if vals:
                        avg_val = sum(vals) / len(vals)
                        if avg_val > K_JAM:
                            density = min(K_JAM, max(5.0, avg_val / 20.0))
                        else:
                            density = max(0.5, avg_val)
                    else:
                        density = 15.0
                        
                    if speeds:
                        raw_spd = sum(speeds) / len(speeds)
                        speed = raw_spd if raw_spd <= 35.0 else raw_spd / 3.6
                    else:
                        # Greenshields Model: v(k) = v_free * (1 - k/k_jam)
                        speed = max(1.5, v_free * (1.0 - min(1.0, density / K_JAM)))
                
                # --- RIGOROUS TRAFFIC PHYSICS EQUATIONS ---
                # 1. Density Bounding
                density = min(K_JAM, max(0.5, density))
                
                # 2. Speed consistency with Greenshields model
                speed = max(1.0, min(v_free * 1.1, speed))
                
                # 3. Occupancy (Space/Time Fraction 0.0 to 1.0)
                occupancy = min(0.98, max(0.02, density / K_JAM))
                
                # 4. Physical Queue Dynamics (HCM / SUMO)
                congestion_ratio = max(0.0, 1.0 - (speed / v_free))
                density_ratio = density / K_JAM
                estimated_queue = congestion_ratio * density_ratio * max_capacity
                
                # If approach has traffic light or node junction, account for cyclic queuing
                if getattr(edge, "signal_group_id", -1) != -1:
                    cyclic_queue = density_ratio * min(6, max_capacity)
                    estimated_queue = max(estimated_queue, cyclic_queue)
                    
                queue = min(max_capacity, max(0, int(round(estimated_queue))))
                
                traffic_list.append({
                    "edge_id": edge_id,
                    "density": float(density),
                    "speed": float(speed),
                    "queue": int(queue),
                    "occupancy": float(occupancy)
                })
        else:
            # Fallback path: iterate raw data items
            for source_id, metrics in data.items():
                if "density" in metrics or "speed" in metrics:
                    d = float(metrics.get("density", 15.0))
                    s = float(metrics.get("speed", 13.89))
                else:
                    d = float(metrics.get("value", 15.0))
                    v = 0.0
                    if "physics" in metrics:
                        v = float(metrics["physics"].get("v", 0.0))
                    s = v if v > 0.5 else 13.89

                d = min(K_JAM, max(0.5, d))
                s = max(1.0, min(25.0, s))
                occ = min(0.98, max(0.02, d / K_JAM))
                q = int(round((1.0 - min(1.0, s / 13.89)) * (d / K_JAM) * 15))

                traffic_list.append({
                    "edge_id": str(source_id),
                    "density": d,
                    "speed": s,
                    "queue": q,
                    "occupancy": occ
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
        _build_time_ms = (_build_end - _build_start) * 1000.0

        # Log Output Traffic Packet to JSONL dump
        try:
            carina_output_logger.log({
                "timestamp": packet["timestamp"],
                "iso_time": datetime.now().isoformat(),
                "source": source,
                "total_edges": len(traffic_list),
                "build_time_ms": round(_build_time_ms, 2),
                "traffic": traffic_list
            })
        except Exception:
            pass

        carina_logger.info(
            f"KSE_BUILD | mode={source} | edges={len(traffic_list)} "
            f"| start={_ts_start} | end={_ts_end} "
            f"| build_time={_build_time_ms:.2f}ms"
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
                v = float(metrics["physics"].get("v", 0.0))
                current_val = float(metrics.get("value", 10.0))
                new_metrics["value"] = max(0.1, current_val + (v * dt))

            if "density" in metrics:
                new_metrics["density"] = max(0.1, float(metrics.get("density", 10.0)))

            if "speed" in metrics:
                s = float(metrics.get("speed", 40.0))
                new_metrics["speed"] = s if s > 0.5 else 40.0

            extrapolated[source_id] = new_metrics

        return extrapolated
