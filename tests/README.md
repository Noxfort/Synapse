# SYNAPSE Testing & Quality Assurance Suite

> **Comprehensive Test Suite, Integration Pipelines, Benchmarks, and Mocks**

---

## 🧪 Overview

The `tests/` directory contains an enterprise test harness designed to guarantee mathematical accuracy, zero-trust security boundaries, real-time throughput, and fault tolerance across **SYNAPSE CORE**.

---

## 📂 Test Suite Structure

```text
tests/
├── conftest.py                # Global PyTest fixtures, state mocks, and CUDA fallbacks
├── benchmark.py               # Hardware stress testing and VRAM/RAM/FPS benchmark
├── mock_grpc_server.py        # Standalone mock of the CARINA gRPC traffic controller
├── mock_sensors.py            # Simulated ingestion sensor feeder (Stress generator)
├── unit/                      # 50+ Unit test suites
│   ├── test_afb_engine.py     # SensorGuard and fallback state machines
│   ├── test_agents.py         # MARKVART™ neural agent execution
│   ├── test_amp_tensorcore.py # Mixed precision & TF32 acceleration
│   ├── test_app_state_solid.py# Domain facade thread safety & state
│   ├── test_corrector_pinn.py # Physics-informed loss & autoencoder
│   ├── test_fuser_deeponet.py # DeepONet operator convergence
│   ├── test_fuser_diffusion_pinn.py # PINO & GATv2 spatial diffusion
│   ├── test_grpc_solid_architecture.py # HFT-Link client & serializer
│   ├── test_ipc_solid.py      # StdioDaemon JSON-RPC protocol
│   ├── test_kse_filter.py     # Extended Kalman Filter & dead reckoning
│   ├── test_linguist_pinn.py  # NeuroSymbolic gatekeeper & DistilRoBERTa
│   └── test_physics_pinn.py   # LWR continuum conservation equations
├── integration/               # End-to-end integration tests
│   ├── test_global_cycle.py   # Full ADAGIO cycle with mock sensors
│   ├── test_grpc_latency.py   # Sub-250ms HFT streaming latency validation
│   ├── test_latency_benchmark.py # Real-time cycle jitter profiling
│   └── test_orchestrator.py   # Multi-thread worker orchestration
└── mocks/                     # Mock data fixtures and synthetic Parquet generators
```

---

## 🚀 Running Tests

### 1. Execute All Tests
```bash
# Run entire test suite with verbose output
pytest tests/ -v
```

### 2. Run Specific Test Layers
```bash
# Run unit tests only
pytest tests/unit/ -v

# Run integration & latency tests only
pytest tests/integration/ -v

# Filter tests matching a keyword
pytest tests/ -k "pinn or deeponet or itransformer" -v
```

### 3. Generate Code Coverage Report
```bash
# Generate terminal report and HTML coverage directory
pytest --cov=src --cov-report=term-missing --cov-report=html:coverage_html tests/
```

---

## ⚡ Performance & Stress Benchmarks

### 1. Full Hardware Stress Benchmark (`tests/benchmark.py`)
Measures CPU utilization, RAM usage, NVIDIA GPU VRAM consumption, and cycle frame rate (FPS):

```bash
# Run standard 60-second stress benchmark with 50 synthetic sensors
python tests/benchmark.py

# Custom duration & sensor scaling (e.g. 150 sensors for 120 seconds)
python -c "from tests.benchmark import run_benchmark; run_benchmark(num_sensors=150, duration=120)"
```

### 2. Mock CARINA Controller (`tests/mock_grpc_server.py`)
Spins up a lightweight gRPC server listening on port `50051` to test the HFT-Link client without needing the external CARINA controller engine:

```bash
# Start standalone Mock CARINA gRPC server
python tests/mock_grpc_server.py
```

### 3. Continuous Sensor Feeder (`tests/mock_sensors.py`)
Generates real-time synthetic traffic telemetry across $N$ data sources:

```bash
# Stream 25 mock sensors through the full ingestion pipeline
python tests/mock_sensors.py 25
```

---

## 🛡️ Best Practices for Writing Tests

1. **Use Standard Fixtures**: Import `mock_app_state`, `sample_map_topology`, or `torch_device` from `tests/conftest.py`.
2. **Deterministic Tensor Tests**: Always set `torch.manual_seed(42)` and `numpy.random.seed(42)` when verifying loss convergence or model gradients.
3. **CPU Fallback Validation**: Ensure tests execute correctly both on CUDA devices and in CI environments without dedicated GPUs.

---

<p align="center">
  <sub>SYNAPSE Testing & QA — Noxfort Systems Reliability Engineering</sub>
</p>
