# SYNAPSE Core Architecture (Low Level)

This document provides a low-level dissection of the SYNAPSE intelligent perception platform. For high-level overviews, refer to the `README.md`.

## 1. Annotated Directory Structure

The SYNAPSE repository is structured strictly around Domain-Driven Design (DDD) and MVC.

```text
SYNAPSE_CORE/
├── src/                      # Backend (Python Core)
│   ├── domain/               # Core business logic entities and State (AppState, MapNode, MapEdge)
│   ├── models/               # Pure PyTorch neural network definitions (.py equivalents of the math)
│   ├── agents/               # Wrappers around models that handle instantiation, training loops, and scaling
│   ├── controllers/          # Business logic handlers (SystemController, ProjectController)
│   ├── phases/               # The ADAGIO Execution phases (Optimization, Bootstrap, Runtime)
│   ├── infrastructure/       # Network, IO, and external APIs (GrpcConnector, PostgresManager)
│   ├── engine/               # Real-time Execution Loop (InferenceEngine, CycleProcessor)
│   └── kse/                  # Kinematic State Estimation (Dead Reckoning for dropped packets)
├── ui/                       # Frontend (PyQt6)
│   ├── components/           # Reusable UI parts (MainMenu, DockManager)
│   ├── controllers/          # View Controllers (MapController)
│   ├── styles/               # ThemeManager and QSS stylesheets
│   └── main_window.py        # The primary Application Window
├── proto/                    # Protobuf definitions for HFT-Link
└── docs/                     # Comprehensive Technical Library
```

## 2. Design Patterns Applied

SYNAPSE strictly adheres to SOLID principles by leveraging several established design patterns:

### The Facade Pattern
- **`AppState` (`src/domain/app_state.py`)**: Acts as a strict facade protecting the `TopologyRepository` and `SourceRepository`. UI components never modify repositories directly; they pass through `AppState` which ensures Zero-Trust synchronization.
- **`MainController` (`src/main_controller.py`)**: The central entry point that wires all signals between the Domain and the UI. It delegates heavy lifting to `SystemController` and `ProjectController`.

### The Strategy & State Patterns
- **`SourceStatus`**: Sensors move through a strict State Machine (`QUARANTINE` $\rightarrow$ `VALIDATING` $\rightarrow$ `ACTIVE` $\rightarrow$ `FALLBACK`). 
- **Graceful Degradation**: Depending on the state, the `CycleProcessor` uses a Strategy pattern to decide how to extract data (Neural Inference for `ACTIVE` sensors vs. Historical MEH lookups for `FALLBACK` sensors).

### Dependency Injection (DIP)
High-level orchestrators (`InferenceEngine`, `RuntimeLauncher`) do not instantiate their own database connections or ML models. They expect `AppState` and `GraphManager` to be injected via constructors, allowing for full unit testing without spinning up PostgreSQL or CUDA.

## 3. The Data Flow Pipeline (End-to-End)

Understanding how a single speed reading from a camera becomes a global traffic adjustment:

1. **Ingestion (`api_ingestor.py`)**: A JSON packet arrives via HTTP. It is mapped to a `DataSource` entity.
2. **State Validation (`app_state.py`)**: If the `DataSource` is `QUARANTINE`, the `payload` is routed to the `Linguist Standby Thread` where `NeuroSymbolic` checks for semantic physics (e.g. Speed cannot be negative).
3. **Graph Memory (`traffic_node.py`)**: Upon validation, the payload updates the `latest_value` of its associated `MapNode` in memory.
4. **Local Feature Extraction (`specialist_agent.py`)**: During the `tick()`, the node pushes the reading through its local TCN to generate a temporal embedding.
5. **Snapshot Build (`snapshot_builder.py`)**: At cycle end, all node embeddings are concatenated into a `sensor_snapshot` tensor matrix.
6. **Global Fusion (`fuser_agent.py`)**: The `iTransformer` receives the snapshot and outputs the "Perfect Present State".
7. **Transport (`grpc_connector.py`)**: The state is serialized via Protobuf and fired over the `HFT-Link` to CARINA in under 250ms.

For deeper technical breakdowns of these steps, please consult the `docs/` library.
