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
# File: src/services/xai_explainer_service.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import torch
from typing import Callable, List, Tuple
from captum.attr import IntegratedGradients

from src.interfaces.xai import IXAIExplainer
from src.utils.logging_setup import get_logger

logger = get_logger("XAI.ExplainerService")


class CaptumExplainerService(IXAIExplainer):
    """
    Mathematical Attribution Service leveraging Captum's Integrated Gradients.
    Decoupled from Qt, threading, and higher-level presentation concerns.
    """

    def compute_attributions(
        self,
        model_wrapper: Callable[[torch.Tensor], torch.Tensor],
        input_vector: List[float],
        device: torch.device
    ) -> Tuple[List[float], float]:
        """
        Computes feature attributions and convergence delta using Integrated Gradients.
        """
        input_tensor = torch.tensor([input_vector], dtype=torch.float32, device=device)
        input_tensor.requires_grad = True

        ig = IntegratedGradients(model_wrapper)
        baseline = torch.zeros_like(input_tensor)

        attributions, delta = ig.attribute(
            inputs=input_tensor,
            baselines=baseline,
            return_convergence_delta=True
        )

        attr_list = attributions.cpu().detach().numpy().flatten().tolist()
        convergence_delta = delta.item() if hasattr(delta, "item") else float(delta)

        return attr_list, convergence_delta
