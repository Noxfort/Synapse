# 05. Data Ingestion & HFT Network

The `src/infrastructure/` directory contains all components that interface with the outside world. It is divided into two distinct responsibilities: **Ingestion** (getting data into SYNAPSE) and **Transport** (sending data to CARINA).

## 1. The Ingestion Pipeline

Data enters SYNAPSE asynchronously. The system cannot assume that APIs will respond quickly or that hardware sensors will maintain stable UDP streams.

### `api_ingestor.py` & `sensor_gateway.py`
- These modules run inside the **Ingestion Thread**.
- They map arbitrary JSON responses or UDP byte streams into the standard `DataSource` entity.
- The thread calls `check_global_fetch(now)` every cycle. If data is ready, it is routed through the `app_state` (applying Zero-Trust logic if it's a new source) and eventually updates the `latest_value` property of the sensor.

### `postgres_manager.py`
- Handles the construction of the Data Lake.
- Continuously dumps the validated traffic telemetry into compressed columnar `.parquet` files for use in the Phase 1 Offline Bootstrap.

## 2. The HFT-Link (High-Frequency Transport)

Located in `grpc_connector.py`, the HFT-Link is the primary communication bridge between SYNAPSE and CARINA. 

### Latency & Payload Tuning
Because traffic matrices and topological graphs can grow extremely large (representing entire cities):
- **Max Message Length**: Hardcoded to `50 MB` (`50 * 1024 * 1024` bytes) to prevent payload truncation when uploading the SUMO `.net.xml` graph.
- **KeepAlive Policies**: Configured to ping every `30s` with a timeout of `10s` to bypass restrictive firewalls and detect dead links aggressively without waiting for default TCP timeouts.

### The 4-Stage Protocol

The connection operates in a strict procedural sequence:

1. **Stage 1: Handshake (`Ping()`)**
   - Verifies the CARINA server is alive.
2. **Stage 2: Topology Upload (`LoadScenario()`)**
   - SYNAPSE packs the SUMO network structure (nodes, edges, logic) into a compressed Protobuf payload via `HFTSerializer`. CARINA builds its internal graph based on this.
3. **Stage 3: Control (`SystemControl()`)**
   - SYNAPSE dictates the state (`START`, `STOP`, `PAUSE`). Sending `START` arms the system.
4. **Stage 4: Streaming Orchestration (`StreamTraffic()`)**
   - A continuous, unidirectional stream of `TrafficFrame` objects. The `HFTStreamer` batches the neural outputs from the `iTransformer` and yields them to CARINA.

### Auto-Recovery Self-Healing Loop

Urban environments suffer from intermittent network drops. The `GrpcConnector` implements an advanced Auto-Recovery loop (`_perform_auto_recovery`):

1. **Payload Caching**: During Stage 2, SYNAPSE caches the serialized map definition (`_recovery_payload`).
2. **Disconnection Handling**: If `grpc.StatusCode.UNAVAILABLE` is received, the application does *not* crash.
3. **Ping Loop**: The thread enters a blocking `while` loop, aggressively pinging CARINA.
4. **Seamless Resume**: Once CARINA comes back online, SYNAPSE transparently:
   - Re-uploads the cached map.
   - Re-arms the system with a `START` command.
   - Resumes the traffic stream seamlessly, allowing the intelligent perception platform to recover from network partitions automatically.
