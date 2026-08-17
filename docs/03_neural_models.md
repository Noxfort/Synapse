# 03. Neural Models & Math (MARKVART™)

The `src/models/` directory contains the pure PyTorch implementations of the 11 specialized neural architectures that make up the MARKVART™ system. The `src/agents/` directory wraps these models with training loops, GPU memory management (`autocast`), and dimensionality protections.

This document details the low-level mechanics of the most critical networks.

## 1. Global Fusion: `iTransformer` (`itransformer.py`)

The *Inverted Transformer* (Liu et al., 2024) is the core of the `FuserAgent`. 
Traditional transformers (like those in NLP) treat time steps as tokens. This fails in multivariate traffic data because traffic variables (speed, flow) are heterogeneous and have different scales.

**The Mathematical Inversion**:
Instead of $N$ variables over $T$ time steps resulting in $T$ tokens of size $N$, the iTransformer creates $N$ tokens of size $T$. 
**Each token represents a single sensor's entire time-series history.**

- **Architecture**:
  - The series of length $T$ is passed through an MLP to project it into a `d_model` dimensional space.
  - A standard Self-Attention mechanism is applied. Because tokens represent sensors, the Attention Matrix natively learns the *cross-sensor correlations* (e.g., Sensor A's history strongly predicts Sensor B's current state).
- **Usage in SYNAPSE**: 
  - We use `pred_len=1`. We are not forecasting the future; we are fusing the history to generate a mathematically sound estimation of the *present state* (t=0) to correct any physical latency or sensor jitter.

## 2. Spatial Reasoning: `GATv2 Lite` (`gatv2_lite.py`)

The `CoordinatorAgent` uses a Graph Attention Network v2 (Brody et al., 2022) to propagate information topologically.

- **Why GATv2?**: Standard GAT computes static attention coefficients. GATv2 introduces dynamic attention, meaning the attention weight between Node A and Node B can change depending on the current traffic state (e.g., A attends to B during morning rush, but ignores B during evening rush).
- **Implementation**: Uses `torch_geometric.nn.GATv2Conv`.
- **Logic**: 
  - Input: Node features (from the TCN) and `edge_index` (from the `MapEdge` definitions).
  - Multi-Head Attention (4 heads) computes $e_{ij} = a(W x_i, W x_j)$.
  - The output node embedding is a weighted sum of its neighbors' features, allowing upstream congestion to mathematically penalize the speed estimation of downstream nodes.

## 3. Local Feature Extraction & Denoising: `TCNAE` (`tcn_ae.py`)

Each `SpecialistAgent` owns a featherweight Temporal Convolutional Autoencoder (TCN-AE).

- **Architecture**: Symmetrical Causal 1D Convolutional Autoencoder (`TCNAEEncoder` + `TCNAEDecoder`) with weight normalization, residual connections, and parameterized causal padding (`Chomp1d`).
- **Footprint**: Ultra-lightweight configuration (`channels=[8, 16]`, `latent_dim=32`), totaling **~3,500 parameters (< 20 KB VRAM per node)**.
- **Warmup & Freeze Lifecycle**:
  - *Cold-Start / Warmup*: When a node initializes, the network adapts locally for 5-10 ticks until reconstruction loss falls below threshold.
  - *Freeze Phase*: Upon validation, weights are locked (`requires_grad=False`). The node runs inference-only in $< 0.01\text{ ms}$, with reconstruction error acting as a zero-cost local anomaly detector.

## 4. Anomaly Detection: `WaveletAE-OCC` (`wavelet_ae_occ.py`)

The `AuditorAgent` is responsible for detecting systemic failures or cyber attacks.

- **Wavelet Scattering**: Uses the `kymatio` library. It acts as a translation-invariant front-end. It breaks the signal into frequency bands, making the anomaly detection robust against slight temporal shifts (e.g., rush hour starting 10 minutes late).
- **Deep SVDD (One-Class Classifier)**: The Autoencoder is trained to map normal traffic states into a tight hypersphere in the latent space.
- **Inference**: If a new traffic snapshot maps outside the EMA (Exponential Moving Average) boundary of this hypersphere ($\mu + 2\sigma$), it is flagged as `DRIFT` or `ATTACK`, triggering the `JuristAgent` to generate an audit report.

## 5. Temporal Imputation: `PatchTST` (`patch_tst.py`)

Replaced the legacy TimeGAN. Used by the `ImputerAgent` to fill data gaps.
- **Mechanism**: Segments the time series into sub-patches. By learning patch-level dependencies rather than point-level, it avoids temporal data leakage and handles long sequences of `NaN` values significantly better than RNN-based imputers.
