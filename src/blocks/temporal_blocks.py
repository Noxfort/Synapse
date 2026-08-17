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
# File: src/blocks/temporal_blocks.py
# Author: Gabriel Moraes
# Date: 2026-08-17

import torch
import torch.nn as nn
from typing import Optional

try:
    from torch.nn.utils.parametrizations import weight_norm
except ImportError:
    from torch.nn.utils import weight_norm


class Chomp1d(nn.Module):
    """
    Utility layer to crop the output of a Conv1d to ensure causal padding.
    Removes the extra padding from the right (future) timesteps.
    """
    def __init__(self, chomp_size: int):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.chomp_size == 0:
            return x
        return x[:, :, :-self.chomp_size].contiguous()


class CausalConv1d(nn.Module):
    """
    Causal 1D Convolution with parameterized weight normalization.
    Trims future padding dynamically to guarantee strict temporal causality.
    """
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        stride: int = 1,
        dilation: int = 1
    ):
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.conv = weight_norm(
            nn.Conv1d(
                in_channels=in_channels,
                out_channels=out_channels,
                kernel_size=kernel_size,
                stride=stride,
                padding=self.padding,
                dilation=dilation
            )
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv(x)
        if self.padding > 0:
            out = out[:, :, :-self.padding].contiguous()
        return out


class TemporalBlock(nn.Module):
    """
    Dilated Causal Temporal Residual Block.
    
    Structure:
    Input -> [Dilated Causal Conv -> Chomp/Trim -> ReLU -> Dropout] x2 -> Output
          \\_____________________________________________________________/
                                         |
                            Residual Link (1x1 Conv if channel dimensions differ)
    """
    def __init__(
        self,
        n_inputs: int,
        n_outputs: int,
        kernel_size: int,
        stride: int = 1,
        dilation: int = 1,
        padding: Optional[int] = None,
        dropout: float = 0.1
    ):
        super(TemporalBlock, self).__init__()
        
        pad_val = (kernel_size - 1) * dilation if padding is None else padding
        
        # --- First Conv Layer ---
        self.conv1 = weight_norm(nn.Conv1d(
            n_inputs, n_outputs, kernel_size,
            stride=stride, padding=pad_val, dilation=dilation
        ))
        self.chomp1 = Chomp1d(pad_val)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        # --- Second Conv Layer ---
        self.conv2 = weight_norm(nn.Conv1d(
            n_outputs, n_outputs, kernel_size,
            stride=stride, padding=pad_val, dilation=dilation
        ))
        self.chomp2 = Chomp1d(pad_val)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(
            self.conv1, self.chomp1, self.relu1, self.dropout1,
            self.conv2, self.chomp2, self.relu2, self.dropout2
        )
        
        # --- Residual Connection ---
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()
        self.init_weights()

    def init_weights(self):
        """Initialize weights with normal distribution."""
        self.conv1.weight.data.normal_(0, 0.01)
        self.conv2.weight.data.normal_(0, 0.01)
        if self.downsample is not None:
            self.downsample.weight.data.normal_(0, 0.01)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)
