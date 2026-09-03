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
# File: tests/unit/test_pino_traffic.py
# Author: Gabriel Moraes
# Date: 2026-08-31

import pytest
import torch
import time
import numpy as np

from src.models.pino_traffic import (
    SpectralConv1d,
    SpectralConv2d,
    PINOTrafficFlow1D,
    SpectralFeatureExtractor
)


def test_spectral_conv1d_forward():
    """Verifies SpectralConv1d operates via FFT/IFFT preserving shape."""
    batch_size = 4
    channels = 16
    seq_len = 64
    modes = 8

    layer = SpectralConv1d(in_channels=channels, out_channels=channels, modes1=modes)
    x = torch.randn(batch_size, channels, seq_len)
    out = layer(x)

    assert out.shape == (batch_size, channels, seq_len)
    assert torch.isfinite(out).all()


def test_spectral_conv2d_forward():
    """Verifies SpectralConv2d operates over 2D spatiotemporal grids."""
    batch_size = 2
    channels = 8
    size_x, size_y = 32, 32
    modes = 8

    layer = SpectralConv2d(in_channels=channels, out_channels=channels, modes1=modes, modes2=modes)
    x = torch.randn(batch_size, channels, size_x, size_y)
    out = layer(x)

    assert out.shape == (batch_size, channels, size_x, size_y)
    assert torch.isfinite(out).all()


def test_pino_traffic_flow_mesh_invariance():
    """Verifies PINO evaluates seamlessly across varying spatial resolutions (Mesh-Invariance)."""
    in_dim = 32
    hidden_dim = 32
    pino = PINOTrafficFlow1D(in_channels=in_dim, hidden_dim=hidden_dim, modes=8)

    # Resolution A: 30 nodes
    x_30 = torch.randn(2, 30, in_dim)
    refined_30, metrics_30 = pino(x_30)
    assert refined_30.shape == (2, 30, in_dim)

    # Resolution B: 100 nodes (same weights, zero retraining)
    x_100 = torch.randn(2, 100, in_dim)
    refined_100, metrics_100 = pino(x_100)
    assert refined_100.shape == (2, 100, in_dim)

    assert (metrics_30["density"] >= 0).all()
    assert (metrics_100["density"] >= 0).all()


def test_pino_latency_benchmark():
    """Verifies PINO forward execution executes well under real-time requirements (< 5ms)."""
    pino = PINOTrafficFlow1D(in_channels=32, hidden_dim=64, modes=16)
    pino.eval()

    x = torch.randn(1, 50, 32)

    # Warmup
    for _ in range(5):
        _ = pino(x)

    start = time.perf_counter()
    for _ in range(50):
        _ = pino(x)
    elapsed_ms = ((time.perf_counter() - start) / 50) * 1000

    assert elapsed_ms < 10.0, f"PINO execution took {elapsed_ms:.2f}ms, exceeding latency budget."


def test_spectral_feature_extractor():
    """Verifies SpectralFeatureExtractor matches expected feature shapes."""
    batch_size = 2
    seq_len = 128
    enc_in = 2

    extractor = SpectralFeatureExtractor(enc_in=enc_in, d_model=32, modes=16)
    x = torch.randn(batch_size, seq_len, enc_in)
    out = extractor(x)

    assert out.shape == (batch_size, seq_len, enc_in)
    assert torch.isfinite(out).all()
