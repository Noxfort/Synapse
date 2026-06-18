# 04. Execution Phases (ADAGIO™)

The system lifecycle is orchestrated by three highly isolated phases located in `src/phases/`. 

## Phase 0: Optimization (`optimization_phase.py`)

This phase handles Calculus-Based AutoML using Optuna.
- **Prerequisites**: Requires at least one live local sensor, one global sensor, and the SUMO Map topology.
- **Execution**: Spins up the `OptimizerService` in a dedicated background thread (`opt_thread`). 
- **Operation**: Optuna explores the hyperparameter space (Tree-structured Parzen Estimator) to calibrate the local TCNs against the topological constraints of the GATv2.

## Phase 1: Offline Bootstrap (`bootstrap_phase.py`)

Generates the "Golden Dataset" baseline from historical `.parquet` files.

### Intelligent Skip & Security Hardening
Training neural networks on terabytes of historical traffic data takes hours. SYNAPSE employs an "Intelligent Skip" to bypass this if the Data Lake is intact.

However, filesystem corruption is common. The `_check_existing_datalake()` method implements **Ghost File Protection**:
```python
# A file existing is not enough. It must not be an empty 0-byte ghost file.
ontology_valid = os.path.exists(safetensors_path) and os.path.getsize(safetensors_path) > 0
```
It validates the entire trifecta:
1. Base `.parquet` files.
2. The `ontology.safetensors` model weights.
3. The `peak_schedule.json` (The Master Lock containing the GMM classified temporal peaks).
If any file is missing or corrupted to 0 bytes, Phase 1 forcefully recompiles the Data Lake.

## Phase 2: Online Runtime (`runtime_phase.py`)

The most critical phase. `RuntimePhase` acts as a Facade coordinating two distinct sub-systems:
1. **`RuntimeConnector`**: Manages the network (`grpc_connector.py`), ensuring the connection to CARINA is stable.
2. **`RuntimeLauncher`**: Manages the compute (`inference_engine.py`), spinning up the 4-Thread architecture.

### The 4-Thread Architecture (Inference Engine)

To guarantee sub-second real-time capability, tasks are isolated by thread:
1. **The Ingestion Thread**: Polls external HTTP endpoints asynchronously.
2. **The Linguist Standby Thread**: Awakens only when a sensor enters `QUARANTINE`. Runs the `NeuroSymbolic` validation without halting the main graph.
3. **The XAI Ephemeral Threads**: When the `AuditorAgent` detects an anomaly, a thread is spawned on-demand to run the `Qwen3` LLM and generate a legal report. It dies immediately after.
4. **The Neural Core Thread**: Runs the strict, synchronous `CycleProcessor` loop.

### KSE Dead Reckoning
During the Core Thread's loop, every intersection (`MapNode`) is ticked. If a sensor drops a packet (e.g. UDP loss), the `Kinematic State Estimation (KSE)` module takes over. It executes `ghost_step()`, invoking Newtonian kinematic equations mixed with historical decay to extrapolate the traffic state. This ensures the GATv2 and iTransformer *never* receive a `NaN` tensor, preventing total system collapse.
