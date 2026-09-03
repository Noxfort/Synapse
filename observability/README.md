# SYNAPSE Observability — Metrics, Dashboards & Telemetry

> **Production Monitoring Stack with Prometheus, Grafana, and TensorBoard**

---

## 📊 Overview

The `observability/` directory contains containerized infrastructure to monitor **SYNAPSE CORE** in real time. It enables traffic engineers and DevOps teams to track sensor health, neural inference jitter, gRPC transmission throughput, memory utilization, and model convergence.

---

## 🐳 Observability Stack Components

| Service | Port | Default Credentials | Description |
| :--- | :--- | :--- | :--- |
| **Prometheus** | `9090` | *None* | Time-series database scraping telemetry metrics from SYNAPSE Core. |
| **Grafana** | `3000` | `admin` / `synapse123` | Real-time monitoring dashboards, heatmaps, and alert rules. |
| **TensorBoard** | `6006` | *None* | Deep learning training visualizer for Phase 0 (Optuna) and Phase 1 training runs. |

---

## 🚀 Quickstart

To spin up the entire observability stack with Docker Compose:

```bash
# Navigate to observability directory
cd observability

# Launch all monitoring services in background
docker compose up -d

# Verify container statuses
docker compose ps
```

To stop the services:
```bash
docker compose down
```

---

## 📈 Metric Dictionary

SYNAPSE Core exports key performance and telemetry metrics:

### 1. High-Frequency Transport (HFT) Metrics
- `synapse_hft_fps`: Number of traffic frames transmitted per second over gRPC.
- `synapse_hft_latency_ms`: Round-trip transmission latency from snapshot creation to gRPC ACK.
- `synapse_hft_bytes_sent_total`: Total network bytes streamed to downstream controllers (CARINA).
- `synapse_hft_reconnections_total`: Number of auto-recovery reconnection events.

### 2. Neural Inference & Execution Pipeline
- `synapse_cycle_duration_ms`: Total execution time of a single ADAGIO perception cycle.
- `synapse_model_latency_ms{model="pino"}`: Individual execution latency per MARKVART™ model.
- `synapse_kse_dead_reckoning_count`: Number of sensors currently evaluated via kinematic dead reckoning.
- `synapse_anomalies_detected_total`: Counter of out-of-distribution events flagged by WaveletAE-OCC.

### 3. Sensor Topology & Trust Health
- `synapse_sensors_count{status="active"}`: Number of sensors in `ACTIVE` inference mode.
- `synapse_sensors_count{status="quarantine"}`: Sensors undergoing zero-trust validation.
- `synapse_sensors_count{status="fallback"}`: Failing sensors serviced via MEH/AFB historical fallback.
- `synapse_sensor_trust_score{source_id="..."}`: Current Bayesian confidence score per sensor ($0.0 \dots 1.0$).

### 4. Hardware & System Resources
- `synapse_cpu_percent`: Process CPU utilization across all worker threads.
- `synapse_gpu_vram_mb`: Dedicated NVIDIA GPU memory consumption.
- `synapse_system_ram_mb`: Host system RAM allocated to graph buffers and Parquet caches.

---

## 📁 Directory Structure

```text
observability/
├── docker-compose.yml         # Multi-container orchestration specification
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── datasource.yml # Auto-configures Prometheus as default datasource
└── prometheus/
    └── prometheus.yml         # Scrape targets (5s interval, host.docker.internal bridge)
```

---

## ⚙️ Host-to-Container Network Configuration

When running SYNAPSE on the host OS and Prometheus inside Docker, Prometheus connects via `host.docker.internal:8000` (or `172.17.0.1:8000` on standard Linux Docker bridges).

If using custom subnets or firewall rules, ensure port `8000` (telemetry endpoint) is accessible from Docker bridge interfaces.

---

<p align="center">
  <sub>SYNAPSE Observability — Noxfort Systems Operations & SRE</sub>
</p>
