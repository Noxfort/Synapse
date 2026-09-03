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
# File: src/physics/sensor_physical_validator.py
# Author: Gabriel Moraes
# Date: 2026-08-31

from typing import Any, List, Optional, Tuple, Dict
import numpy as np
import logging

from src.interfaces.quarantine import ISensorPhysicsValidator, ISemanticClassifier
from src.services.semantic_classifier import SemanticClassifier
from src.domain.entities import DataSource, MapEdge

logger = logging.getLogger("Synapse.Physics.SensorPhysicalValidator")

# Traffic Engineering Constants (Highway Capacity Manual / Real-world Urban Standards)
DEFAULT_CAPACITY_PER_LANE_VEH_H: float = 2400.0  # Max saturation flow per lane (veh/h)
SATURATION_FLOW_RATE_PER_SEC: float = 0.67       # ~2400 / 3600 (veh/s/lane)
DEFAULT_JAM_DENSITY_PER_LANE: float = 160.0      # Jam density per lane (veh/km)
DEFAULT_URBAN_SPEED_LIMIT_KMH: float = 60.0      # Default urban street speed (km/h)
MAX_URBAN_SPEED_CEILING_KMH: float = 200.0       # Absolute physical speed ceiling for road vehicles (km/h)
MAX_VEHICLE_ACCEL_MS2: float = 12.0              # Max emergency acceleration/braking (m/s^2)


class SensorPhysicalValidator(ISensorPhysicsValidator):
    """
    Validates physical consistency and macroscopic traffic invariants
    using context-aware symbolic rules derived from roadway topology, sampling delta-time (dt),
    engineering units, and Neuro-PINN residual inference.
    """

    def __init__(
        self,
        semantic_classifier: Optional[ISemanticClassifier] = None,
        max_physical_bound: float = 10000.0,
        max_physics_residual: float = 0.5,
        app_state: Optional[Any] = None
    ):
        self.semantic_classifier = semantic_classifier or SemanticClassifier()
        self.max_physical_bound = max_physical_bound
        self.max_physics_residual = max_physics_residual
        self.app_state = app_state

    def validate(
        self,
        source: DataSource,
        data_np: np.ndarray,
        data_chunk: Optional[List[Any]] = None,
        agent: Optional[Any] = None,
        app_state: Optional[Any] = None
    ) -> bool:
        """
        Uses Modality, Topology Context, Sampling dt, and PINN Agent to validate physical feasibility.
        
        Args:
            source: DataSource entity under evaluation.
            data_np: 1D NumPy array of numerical values.
            data_chunk: Optional list of raw payload items.
            agent: Optional LinguistAgent for Neuro-PINN inference check.
            app_state: Optional AppState facade for topology resolution.
            
        Returns:
            bool: True if physically valid, False otherwise.
        """
        if len(data_np) == 0:
            logger.warning(f"⚠️ [Physics] Violação: Nenhum valor numérico válido encontrado nas amostras de '{source.name}'.")
            return False

        active_app_state = app_state or self.app_state
        sem_type, unit, _ = self.semantic_classifier.classify(source, data_np, data_chunk)
        sem_lower = sem_type.lower()

        # 1. Fundamental Non-Negativity Invariant
        if np.min(data_np) < 0:
            logger.warning(f"⚠️ [Physics] Violação: Valor negativo ({np.min(data_np):.2f}) detectado em '{source.name}'.")
            return False

        # 2. Resolve Roadway Topology Context (Lanes, Speed Limits)
        edge = self._resolve_associated_edge(source, active_app_state)
        lanes = int(edge.lanes) if edge and isinstance(getattr(edge, "lanes", None), (int, float)) and edge.lanes > 0 else int(source.metadata.get("lanes", 4))
        dt_sec = self._resolve_sampling_interval(data_chunk, source)

        # 3. Dynamic Modality-Aware Physical Bounds Check
        is_valid_bound, max_bound_desc = self._check_dynamic_bounds(
            data_np=data_np,
            sem_type=sem_type,
            unit=unit,
            lanes=lanes,
            edge=edge,
            dt_sec=dt_sec,
            source=source
        )
        if not is_valid_bound:
            logger.warning(
                f"⚠️ [Physics] Violação: Limite físico dinâmico excedido em '{source.name}'. "
                f"Máximo registrado: {np.max(data_np):.2f} > Teto: {max_bound_desc} (Faixas={lanes}, dt={dt_sec:.2f}s, Unidade={unit})."
            )
            return False

        # 4. Kinematic Acceleration Check (for speed time-series)
        if "speed" in sem_lower and len(data_np) > 1 and dt_sec > 0:
            if not self._check_kinematic_acceleration(data_np, unit, dt_sec, source):
                return False

        # 5. Context-Aware Flatline / Dead Sensor Check
        if not self._check_sensor_liveness(data_np, sem_lower, source):
            return False

        # 6. Neuro-PINN Validation (Conditioned by Modality and Topology)
        if agent is not None and hasattr(agent, "inference"):
            claim = (
                f"Sensor {source.name} ({source.id}) modality {sem_type} [{unit}] "
                f"on {lanes}-lane segment with dt={dt_sec:.2f}s. "
                f"Range [{np.min(data_np):.1f}, {np.max(data_np):.1f}], mean {np.mean(data_np):.1f}."
            )
            analysis = agent.inference({"text": claim, "semantic_type": sem_type})
            if analysis.get('is_anomaly', False) or analysis.get('physics_residual', 0.0) > self.max_physics_residual:
                logger.warning(
                    f"⚠️ [Physics/PINN] Violação: Inconsistência na modalidade '{sem_type}' em '{source.name}' "
                    f"(Resíduo Físico: {analysis.get('physics_residual', 0.0):.4f})."
                )
                return False

        return True

    def _resolve_associated_edge(self, source: DataSource, app_state: Optional[Any]) -> Optional[MapEdge]:
        """Resolves the MapEdge entity linked to the data source if available in the network topology."""
        if app_state is None:
            return None
        
        try:
            element_id = None
            if hasattr(app_state, "get_element_for_source"):
                raw_elem = app_state.get_element_for_source(source.id)
                if isinstance(raw_elem, str) and raw_elem:
                    element_id = raw_elem
            if not element_id:
                raw_meta = source.metadata.get("edge_id") or source.metadata.get("element_id")
                if isinstance(raw_meta, str) and raw_meta:
                    element_id = raw_meta
            
            if element_id and hasattr(app_state, "get_edge"):
                edge = app_state.get_edge(element_id)
                if edge and isinstance(getattr(edge, "lanes", None), (int, float)):
                    return edge
        except Exception as e:
            logger.debug(f"[Physics] Falha ao resolver MapEdge para '{source.id}': {e}")
            
        return None

    def _resolve_sampling_interval(self, data_chunk: Optional[List[Any]], source: DataSource) -> float:
        """Determines the effective sampling interval dt in seconds."""
        # 1. Try extracting delta from timestamps in data_chunk
        if data_chunk and len(data_chunk) >= 2:
            timestamps = []
            for item in data_chunk:
                if isinstance(item, dict):
                    ts = item.get("timestamp") or item.get("time") or item.get("ts") or item.get("event_timestamp")
                    if isinstance(ts, (int, float)) and ts > 0:
                        timestamps.append(float(ts))
            if len(timestamps) >= 2:
                deltas = np.diff(timestamps)
                pos_deltas = deltas[deltas > 0]
                if len(pos_deltas) > 0:
                    return float(np.median(pos_deltas))

        # 2. Check metadata configuration
        dt_meta = source.metadata.get("sampling_interval_sec") or source.metadata.get("dt") or source.metadata.get("interval")
        if isinstance(dt_meta, (int, float)) and dt_meta > 0:
            return float(dt_meta)

        # 3. Safe streaming default
        return 1.0

    def _check_dynamic_bounds(
        self,
        data_np: np.ndarray,
        sem_type: str,
        unit: str,
        lanes: int,
        edge: Optional[MapEdge],
        dt_sec: float,
        source: DataSource
    ) -> Tuple[bool, str]:
        """Calculates dynamic physical limits based on roadway capacity and modality."""
        sem_lower = sem_type.lower()
        max_val = float(np.max(data_np))

        # A. Speed Bounds (m/s, km/h, mph)
        if "speed" in sem_lower:
            if edge and isinstance(getattr(edge, "max_speed", None), (int, float)) and edge.max_speed > 0:
                # edge.max_speed is in m/s in SUMO/SYNAPSE entities
                edge_speed_kmh = edge.max_speed * 3.6
            else:
                edge_speed_kmh = float(source.metadata.get("max_speed_kmh", DEFAULT_URBAN_SPEED_LIMIT_KMH))

            # Allow 35% speed overrun over posted limit for realistic non-conforming drivers
            speed_ceiling_kmh = min(MAX_URBAN_SPEED_CEILING_KMH, max(edge_speed_kmh * 1.35, 40.0))

            if unit.lower() in ["m/s", "mps"]:
                bound = speed_ceiling_kmh / 3.6
                desc = f"{bound:.1f} m/s ({speed_ceiling_kmh:.0f} km/h)"
            elif unit.lower() in ["mph"]:
                bound = speed_ceiling_kmh / 1.60934
                desc = f"{bound:.1f} mph"
            else:
                bound = speed_ceiling_kmh
                desc = f"{bound:.1f} km/h"

            return (max_val <= bound), desc

        # B. Flow Bounds (veh/h, veh/min, veh/s)
        elif "flow" in sem_lower or "fluxo" in sem_lower:
            # Capacity: lanes * capacity_per_lane * 1.25 safety factor
            capacity_veh_h = lanes * DEFAULT_CAPACITY_PER_LANE_VEH_H * 1.25
            if unit.lower() in ["veh/min", "veic/min", "vpm"]:
                bound = capacity_veh_h / 60.0
                desc = f"{bound:.1f} veh/min"
            elif unit.lower() in ["veh/s", "veic/s", "vps"]:
                bound = capacity_veh_h / 3600.0
                desc = f"{bound:.2f} veh/s"
            else:
                bound = capacity_veh_h
                desc = f"{bound:.0f} veh/h"

            return (max_val <= bound), desc

        # C. Count Bounds (discrete detections in time window dt)
        elif "count" in sem_lower or "veic" in sem_lower or "contagem" in sem_lower:
            # Optical FOV capacity (~15 veh/lane) + dynamic flow arrivals during window dt
            fov_capacity = lanes * 15.0
            throughput_capacity = lanes * SATURATION_FLOW_RATE_PER_SEC * max(dt_sec, 1.0) * 1.5
            bound = max(15.0, fov_capacity + throughput_capacity)
            desc = f"{bound:.0f} veic (em dt={dt_sec:.1f}s)"
            return (max_val <= bound), desc

        # D. Density & Occupancy
        elif "density" in sem_lower or "densidade" in sem_lower:
            bound = lanes * DEFAULT_JAM_DENSITY_PER_LANE
            desc = f"{bound:.0f} veh/km"
            return (max_val <= bound), desc
        elif "occupancy" in sem_lower or "ocupacao" in sem_lower:
            bound = 100.0 if max_val > 1.0 else 1.0
            desc = f"{bound:.0f}%"
            return (max_val <= bound), desc

        # E. Generic Modality Fallback
        return (max_val <= self.max_physical_bound), f"{self.max_physical_bound}"

    def _check_kinematic_acceleration(
        self,
        data_np: np.ndarray,
        unit: str,
        dt_sec: float,
        source: DataSource
    ) -> bool:
        """Verifies if acceleration/deceleration between consecutive points is physically plausible."""
        # Convert values to m/s
        if unit.lower() in ["km/h", "kmh"]:
            speeds_ms = data_np / 3.6
        elif unit.lower() in ["mph"]:
            speeds_ms = data_np * 0.44704
        else:
            speeds_ms = data_np

        accels = np.abs(np.diff(speeds_ms)) / max(dt_sec, 0.1)
        max_accel = float(np.max(accels))

        if max_accel > MAX_VEHICLE_ACCEL_MS2:
            logger.warning(
                f"⚠️ [Physics] Violação Cinemática: Aceleração/frenagem impossível ({max_accel:.2f} m/s²) "
                f"detectada em '{source.name}' (Máximo tolerado: {MAX_VEHICLE_ACCEL_MS2} m/s²)."
            )
            return False

        return True

    def _check_sensor_liveness(
        self,
        data_np: np.ndarray,
        sem_lower: str,
        source: DataSource
    ) -> bool:
        """
        Verifies if sensor is truly active.
        Crucial: Vehicle count or density of 0 is valid during off-peak hours (empty roads).
        Only continuous floating-point signals stuck at a non-zero constant with zero machine variance are flagged.
        """
        if len(data_np) < 10:
            return True

        # Discrete counts and density are allowed to be 0 for arbitrary periods (e.g. empty streets at 3 AM)
        if "count" in sem_lower or "dens" in sem_lower:
            return True

        # If a continuous sensor (speed, flow) has zero variance and is stuck on a non-zero float over 20+ samples
        if len(data_np) >= 20 and np.var(data_np) == 0.0 and np.mean(data_np) > 0.0:
            logger.warning(f"⚠️ [Physics] Violação: Sensor travado com valor estático contínuo ({np.mean(data_np):.2f}) em '{source.name}'.")
            return False

        return True

