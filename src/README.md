# SYNAPSE Core — Backend Architecture & Subsystems

> **Internal Architecture Guide for Python Core Services, Neural Inference, and Domain Logic**

---

## 🏛️ Architectural Principles

The backend of **SYNAPSE CORE** is engineered in Python 3.10+ with PyTorch 2.x, adhering to **Domain-Driven Design (DDD)**, **Clean Architecture**, and strict **SOLID** patterns:

1. **Single Responsibility Principle (SRP)**: Every module, service, agent, and pipeline encapsulates a single bounded responsibility.
2. **Open/Closed Principle (OCP)**: New sensors, neural architectures, and optimization strategies are added via abstract interfaces without modifying existing pipelines.
3. **Liskov Substitution Principle (LSP)**: All neural agents implement `BaseAgent`, and all ingestion protocols implement `BaseAdapter`.
4. **Interface Segregation Principle (ISP)**: Interfaces in `src/interfaces/` are finely segregated (e.g., `IEngine`, `INode`, `IMemory`, `ITransport`).
5. **Dependency Inversion Principle (DIP)**: High-level orchestrators depend upon abstract interfaces and receive repositories via Constructor Injection (`ServiceContainer` and `ControllerFactory`).

---

## 📦 Subsystem Directory Breakdown

The `src/` directory contains 35 specialized packages organized into logical layers:

```text
src/
├── domain/            # Core business entities, AppState facade, repositories
├── models/            # PyTorch neural network & operator implementations
├── agents/            # MARKVART™ autonomous neural agents & wrappers
├── blocks/            # Deep learning building blocks (Graph, Spectral, Temporal)
├── physics/           # Continuum traffic physics, LWR PDEs, fundamental diagrams
├── engine/            # Real-time inference engine, cycle runner, and routing
├── node/              # TrafficNode graph vertices, state, and step processing
├── pipeline/          # Agent-specific execution pipelines
├── stages/            # ADAGIO execution stages (Auditor, Classification, Sanitization)
├── strategies/        # Validation, imputation, clustering, and ensemble strategies
├── phases/            # ADAGIO™ lifecycle phases (Optimization, Bootstrap, Runtime)
├── orchestrators/     # HFT and lifecycle orchestrators
├── workers/           # Background thread workers (Ingestion, XAI, Standby)
├── ipc/               # Headless StdioDaemon, JSON-RPC protocol, EventBridge
├── adapters/          # Ingestion adapters (HTTP Push/Poll, MQTT, WebSocket, Replay)
├── infrastructure/    # gRPC client, PostgreSQL manager, SafeTensors storage
├── kse/               # Kinematic State Estimation (Kalman Dead Reckoning)
├── afb/               # Adaptive Fallback Engine & SensorGuard
├── meh/               # Micro-Estimation History & Golden Dataset loader
├── fenix/             # Continuous drift evaluation & self-healing maintenance
├── memory/            # Episodic, Semantic, Spatial, and Spatiotemporal memory
├── optimization/      # Optuna AutoML and Population-Based Training (PBT)
├── trainer/           # Neural training routines for agents
├── factories/         # Factory methods & ServiceContainer for IoC
├── handlers/          # Command and database event handlers
├── managers/          # Graph, Node, Source, Storage, and XAI managers
├── services/          # Domain services (MapService, LinguistService, FenixService)
├── interfaces/        # Abstract Base Classes and Typing Protocols
├── mixins/            # Reusable behavior mixins (e.g., PBTMixin)
├── prompts/           # LLM Jinja2 prompt configurations (Multi-language)
├── templates/         # Prompt templates for Jurist XAI reports
├── logging/           # Centralized logging facade and interceptors
└── utils/             # Hardware acceleration, geometry, normalization helpers
```

---

## 🔬 Core Subsystems in Detail

### 1. `domain/` — The Core Domain Model
- **`entities.py`**: Defines core dataclasses (`DataSource`, `MapNode`, `MapEdge`, `DataAssociation`, `SourceType`, `SourceStatus`).
- **`app_state.py`**: Thread-safe Domain Facade protecting the `TopologyRepository` and `SourceRepository`. Ensures atomic state transitions.
- **`source_repository.py` & `topology_repository.py`**: In-memory, zero-trust repositories storing sensors and the SUMO graph.
- **`model_contracts.py`**: Data contracts and tensor shapes passed between neural models.

### 2. `models/` — Pure PyTorch Neural Operators & Transformers
- **`pino_traffic.py`**: Physics-Informed Neural Operator utilizing 1D/2D Fourier Spectral Convolutions and Lighthill-Whitham-Richards (LWR) conservation laws $\frac{\partial \rho}{\partial t} + \frac{\partial q}{\partial x} = 0$.
- **`pi_deeponet.py`**: Dual-network Branch/Trunk Deep Operator Network for continuous spatial-temporal velocity/density field interpolation.
- **`pi_vae_tcn.py`**: Physics-Informed Variational Autoencoder with Dilated Causal Convolutions for generative noise filtering.
- **`itransformer.py` & `itransformer_lite.py`**: Inverted Multi-Variate Transformer embedding time-series as tokens with spatial cross-attention.
- **`gatv2_lite.py` & `diffusion_gatv2.py`**: Dynamic Graph Attention Networks with spatial graph diffusion.
- **`sinkhorn_cross_attention.py`**: Differentiable Optimal Transport map matcher.
- **`wavelet_ae_occ.py`**: Discrete Wavelet Transform Autoencoder with One-Class Deep SVDD anomaly score.
- **`tcn_ae.py`**: Temporal Convolutional Autoencoder for local sensor temporal embedding.
- **`neuro_symbolic.py` & `distilroberta.py`**: Frozen transformer language embeddings combined with symbolic rule checking for zero-trust ingestion.

### 3. `agents/` — MARKVART™ Autonomous Neural Agents
Each agent wraps one or more models from `models/`, managing tensor preparation, device allocation, inference, and online adaptation:
- `SpecialistAgent`: Runs local TCN inference per active sensor.
- `CorrectorAgent`: Runs PI-VAE-TCN to clean noisy readings.
- `LinguistAgent`: Performs semantic validation and schema detection on incoming feeds.
- `CoordinatorAgent`: Aggregates spatial graph context via GATv2.
- `CartographerAgent`: Maps raw latitude/longitude points to road graph edges via Sinkhorn matching.
- `FuserAgent`: Fuses all embeddings into the global "Perfect Snapshot" matrix using iTransformer and PINO.
- `TranslationAgent`: Uncovers cyclical frequency patterns via TimesNet (FFT).
- `ImputerAgent`: Generates synthetic traffic sequences for dead sensors via TimeGAN.
- `AuditorAgent`: Flags out-of-distribution patterns using WaveletAE-OCC.
- `PeakClassifierAgent`: Identifies peak/off-peak schedules using DistilRoBERTa + GMM.
- `JuristAgent`: Produces explainable XAI audit reports via quantized Qwen3 LLMs.

### 4. `engine/` — High-Throughput Inference Engine
- **`inference_engine.py`**: Coordinates the tick execution loop across all active nodes and agents.
- **`cycle_processor.py`**: Executes cycle-level tensor concatenation, batching, and fallback dispatching.
- **`cycle_runner.py`**: High-precision timer thread maintaining exact execution frequencies.
- **`data_flow_router.py`**: Routes incoming telemetry to active nodes vs. fallback queues.
- **`gating_policy.py`**: Decides whether a node's output should be sourced from Neural Inference, KSE Dead Reckoning, or MEH Historical Lookup.

### 5. `physics/` — Continuum Mechanics & Kinematics
- **`continuum.py`**: Spatial graph conservation equations and flux calculations across network junctions.
- **`fundamental_diagrams.py`**: Implementations of Greenshields, Greenberg, Underwood, and Northwestern traffic flow curves ($q = k \cdot v$).
- **`sensor_physical_validator.py`**: Hard physical boundary checks (e.g., negative speed, teleportation velocity, non-physical density bounds).
- **`traffic_loss.py`**: PyTorch custom loss functions enforcing PDE residual penalties $\mathcal{L}_{PINO} = \mathcal{L}_{data} + \lambda \mathcal{L}_{physics}$.

### 6. `ipc/` — Headless Daemon & Sidecar Bridge
- **`stdio_daemon.py`**: Zero-port IPC server listening to JSON-RPC on `sys.stdin` and emitting events to `sys.stdout`.
- **`stdio_transport.py`**: High-performance, non-blocking standard I/O stream handler.
- **`command_router.py`**: Dispatches incoming desktop UI commands to domain handlers.
- **`event_bridge.py`**: Bridges internal Qt signals and telemetry events to frontend IPC payloads.

### 7. `infrastructure/` — External Network & Storage I/O
- **`grpc_connector.py` / `hft_grpc_client.py`**: High-Frequency Transport client streaming `TrafficFrame` protobuf messages.
- **`hft_streamer.py`**: Non-blocking streaming loop with backpressure management.
- **`hft_recovery.py`**: Background auto-recovery worker that re-establishes dropped gRPC connections and re-syncs maps.
- **`sensor_gateway.py`**: Unified gateway for physical and simulated data sources.
- **`postgres_manager.py`**: PostgreSQL database connector for historical persistence.
- **`safetensors_repository.py`**: Zero-copy tensor persistence using the HuggingFace `safetensors` format.

### 8. `afb/`, `kse/`, `meh/`, & `fenix/` — Resilience Quadriad
- **`kse/` (Kinematic State Estimation)**: Extended Kalman Filtering and dead reckoning estimating vehicle counts and queue lengths during network packet drops.
- **`meh/` (Micro-Estimation History)**: High-resolution historical lookup tables extracted from the Golden Dataset.
- **`afb/` (Adaptive Fallback System)**: Fault-tolerant sensor protection engine that dynamically downgrades failing sensors from `ACTIVE` to `FALLBACK` and recovers them through `PROBATION`.
- **`fenix/`**: Long-term model drift monitoring, maintenance scheduling, and online hot-resetting.

---

## 🔄 End-to-End Processing Cycle

A single real-time cycle (typically 1.0 second) executes in strictly orchestrated steps:

```text
1. INGESTION       Raw sensor JSON/MQTT payload arrives at IngestionHub.
2. ZERO-TRUST      Linguist Agent checks schema & physics validity.
3. DEAD RECKONING  KSE Module updates kinematic predictions if packet was delayed.
4. LOCAL EMBED     Specialist Agents execute TCN-AE across active sensor nodes.
5. TOPOLOGY        Coordinator Agent runs GATv2 over the SUMO graph.
6. GLOBAL FUSION   iTransformer + PINO fuse spatial-temporal tokens into Snapshot.
7. AUDIT & XAI     WaveletAE checks anomaly scores; Jurist compiles log if anomalous.
8. HFT TRANSPORT   State is serialized into Protobuf and pushed to CARINA via gRPC.
9. IPC TELEMETRY   EventBridge pushes metrics to Tauri desktop UI via JSON-RPC.
```

---

## 🧵 Concurrency & Threading Model

SYNAPSE executes with a dedicated multi-threaded concurrency architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MAIN THREAD (Qt Core)                           │
│     - QCoreApplication Event Loop & StdioDaemon JSON-RPC Transport     │
│     - SignalRouter dispatching async Qt signals                        │
└───────────────┬────────────────────────────────────────┬───────────────┘
                │ Spawns & Coordinates                   │
┌───────────────▼───────────────┐        ┌───────────────▼───────────────┐
│     Ingestion Worker Thread   │        │   Standby Linguist Thread     │
│  - Consumes HTTP, MQTT, WS    │        │  - Validates quarantined feeds│
│  - Pushes raw queues          │        │  - Runs DistilRoBERTa embed   │
└───────────────────────────────┘        └───────────────────────────────┘
┌───────────────────────────────┐        ┌───────────────────────────────┐
│   Neural Core Engine Thread   │        │     XAI Jurist Worker Thread  │
│  - PyTorch CUDA inference     │        │  - Non-blocking LLM reports   │
│  - KSE Kalman Dead Reckoning  │        │  - Multi-language template gen│
│  - HFT-Link gRPC transmission │        │                               │
└───────────────────────────────┘        └───────────────────────────────┘
```

---

## 🛠️ Developer Guidelines: Adding New Models & Services

### Adding a New Neural Model:
1. Define the PyTorch architecture in `src/models/my_model.py` (ensure `torch.backends.cuda.matmul.allow_tf32 = True` for Tensor Core support).
2. Create the corresponding Agent in `src/agents/my_agent.py` inheriting from `BaseAgent`.
3. Register the agent factory in `src/factories/agent_factory.py`.
4. Add unit and integration tests under `tests/unit/test_my_agent.py`.

### Adding a New Data Ingestion Protocol:
1. Subclass `BaseAdapter` in `src/adapters/my_adapter.py`.
2. Register the protocol in `src/domain/entities.py` (`SourceType`).
3. Connect the adapter inside `src/adapters/ingestion_hub.py`.

---

<p align="center">
  <sub>SYNAPSE CORE — Noxfort Systems Engineering</sub>
</p>
