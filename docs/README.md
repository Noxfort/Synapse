# SYNAPSE Technical Documentation Library

> **Exhaustive Architectural, Mathematical, and Operational Manuals**

---

## 📚 Technical Documentation Index

Welcome to the comprehensive technical documentation library for **SYNAPSE CORE v2.0**. This directory provides deep-dive guides into every subsystem of the platform.

---

### 📖 Available Guides

| Guide | Document Link | Description & Key Topics |
| :--- | :--- | :--- |
| **01. Domain Entities** | [01_domain_entities.md](01_domain_entities.md) | `MapNode`, `MapEdge`, `DataSource`, `SourceStatus` state machines, zero-trust lifecycle, and Bayesian trust hierarchy constants. |
| **02. UI Architecture** | [02_ui_architecture.md](02_ui_architecture.md) | Modern desktop UI design, Tauri v2 Rust sidecar manager, React 18 frontend, Zustand reactive stores, and Zero-Port Stdio IPC. |
| **03. Neural Models & Math** | [03_neural_models.md](03_neural_models.md) | Complete mathematical formulations, loss functions, and PyTorch implementations of the 11 MARKVART™ models (PINO, DeepONet, iTransformer, GATv2, VAE-TCN). |
| **04. Execution Phases** | [04_execution_phases.md](04_execution_phases.md) | ADAGIO™ lifecycle (Phase 0 AutoML, Phase 1 Bootstrap Golden Dataset, Phase 2 Online 4-Thread Concurrency Runtime). |
| **05. Data Ingestion & HFT** | [05_data_ingestion_and_hft.md](05_data_ingestion_and_hft.md) | Sensor adapters (HTTP, MQTT, WebSocket), Protocol Buffers, gRPC streaming, and background self-healing auto-recovery loops. |
| **06. Developer Guide** | [06_developer_guide.md](06_developer_guide.md) | Setting up development environments, compiling Protobuf schemas, extending agents, and executing PyTest suites. |
| **07. Production Deployment** | [07_deployment_guide.md](07_deployment_guide.md) | Headless daemon configuration, `systemd` unit setup, Docker containerization, Debian packaging, and Prometheus/Grafana monitoring. |

---

## 🧭 Suggested Reading Paths

### For Machine Learning & Research Engineers:
1. [01. Domain Entities & Core Structures](01_domain_entities.md)
2. [03. Neural Models & PyTorch Implementations](03_neural_models.md)
3. [04. Execution Phases & Lifecycle](04_execution_phases.md)

### For Systems & Backend Engineers:
1. [01. Domain Entities & Core Structures](01_domain_entities.md)
2. [05. Data Ingestion & HFT Network](05_data_ingestion_and_hft.md)
3. [06. Developer Guide](06_developer_guide.md)
4. [07. Production Deployment Guide](07_deployment_guide.md)

### For Frontend & UI/UX Engineers:
1. [01. Domain Entities & Core Structures](01_domain_entities.md)
2. [02. UI Architecture & Frontend](02_ui_architecture.md)
3. [ui/README.md](../ui/README.md)

---

<p align="center">
  <sub>SYNAPSE Documentation — Noxfort Systems Engineering Library</sub>
</p>
