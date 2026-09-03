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
# File: src/engine/forecast_imputer.py
# Author: Gabriel Moraes
# Date: 2026-08-30

from typing import Any, Dict, Optional
import numpy as np
import torch

from src.interfaces.engine import IForecastImputer
from src.managers.graph_manager import GraphManager


class ForecastImputer(IForecastImputer):
    """
    Propagates neural predictions (GNN / PINN / Transformer forecast)
    to unobserved or missing nodes in the graph and snapshot.
    
    SOLID Responsibility:
    - [SRP] Exclusively performs tensor reshaping, array conversion,
      and propagation into unobserved graph node states.
    - [OCP] Different imputation or decay strategies can be implemented
      or subclassed without modifying the InferenceEngine orchestrator.
    """

    def impute(
        self,
        forecast: Optional[Any],
        snapshot: Dict[str, Any],
        graph_manager: GraphManager
    ) -> None:
        """
        Extracts forecast values and fills in zero/missing values in snapshot and graph nodes.
        """
        if forecast is None or not hasattr(graph_manager, "get_ordered_node_ids"):
            return

        ordered_nodes = graph_manager.get_ordered_node_ids()
        if not ordered_nodes:
            return

        # Convert forecast tensor/array to a flat 1D numpy array
        if isinstance(forecast, torch.Tensor):
            forecast_arr = forecast.detach().cpu().numpy()
        elif isinstance(forecast, np.ndarray):
            forecast_arr = forecast
        else:
            try:
                forecast_arr = np.array(forecast)
            except Exception:
                return

        forecast_flat = forecast_arr.flatten()

        # Match ordered nodes with predicted variates
        for i, nid in enumerate(ordered_nodes):
            if i >= len(forecast_flat):
                break

            pred_val = float(forecast_flat[i])
            if nid in snapshot:
                curr_val = float(snapshot[nid].get("value", 0.0))
                # If current sensor is unobserved (<= 0) and model predicted a valid value (> 0)
                if curr_val <= 0.0 and pred_val > 0.0:
                    snapshot[nid]["value"] = pred_val
                    t_node = graph_manager.get_node(nid)
                    if t_node:
                        if hasattr(t_node, "state") and hasattr(t_node.state, "last_value"):
                            t_node.state.last_value = pred_val
                        elif hasattr(t_node, "last_value"):
                            try:
                                t_node.last_value = pred_val
                            except AttributeError:
                                pass
