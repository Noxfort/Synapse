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
# File: src/utils/hardware.py
# Author: Gabriel Moraes
# Date: 2026-08-29

"""
Hardware and CUDA/TensorCore initialization routines.
"""

def configure_hardware_acceleration() -> None:
    """
    Global Hardware Acceleration & Tensor Core (TF32) Configuration for Ampere+ GPUs.
    Configures PyTorch backends for optimal CUDA / TensorFloat-32 performance.
    """
    try:
        import torch
        if torch.cuda.is_available():
            torch.set_float32_matmul_precision('high')
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
    except Exception:
        pass


__all__ = ["configure_hardware_acceleration"]
