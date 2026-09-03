# SYNAPSE HFT-Link — Protocol Buffers & gRPC Specification

> **High-Frequency Transport Interface for Real-Time Traffic Perception Streaming**

---

## ⚡ Overview

The `proto/` directory contains the official **Protocol Buffers v3** schema defining the **HFT-Link (High-Frequency Transport Link)** between **SYNAPSE CORE** (the perception brain) and downstream traffic controllers like **CARINA** (the macroscopic signal controller).

The HFT-Link is engineered for extreme throughput, sub-250ms cycle latency, and automatic topological synchronization over HTTP/2 gRPC.

---

## 📡 Service Definition (`HFTLink`)

```protobuf
service HFTLink {
  // Liveness check & clock synchronization
  rpc Ping (Empty) returns (SystemState);

  // Synchronizes the road network topology and peak-hour schedules
  rpc LoadScenario (ScenarioDefinition) returns (ScenarioStatus);

  // Operational control (START, PAUSE, STOP, RESET)
  rpc SystemControl (ControlCommand) returns (CommandResponse);

  // High-frequency client-streaming of continuous traffic state frames
  rpc StreamTraffic (stream TrafficFrame) returns (SystemState);
}
```

---

## 📋 Core Message Specifications

### 1. Topology & Scenario Synchronization
- **`ScenarioDefinition`**: Transmits the complete urban topology, compressed SUMO `.net.xml.gz` binary payload, map hash, and peak-schedule clusters.
- **`TopologyGraph`**: Contains all road vertices (`TopologyNode`) and street segments (`TopologyEdge`) with lane counts, speed limits, and NTCIP signal group mappings.
- **`MapGeometry`**: Contains multi-segment polyline coordinates (`MapShape`) for rendering road paths.

### 2. High-Frequency Telemetry (`TrafficFrame`)
Streams real-time edge matrices at frequencies up to 10 Hz:
```protobuf
message TrafficFrame {
  double timestamp = 1;            // Unix epoch timestamp in seconds (float64)
  uint64 sequence_id = 2;          // Monotonically increasing frame index
  map<string, EdgeState> edges = 3;// Map of EdgeID -> Inferred Physical State
}

message EdgeState {
  float occupancy = 1;             // Percentage occupancy [0.0 - 1.0]
  float mean_speed = 2;            // Mean edge velocity (m/s or km/h)
  int32 queue_length = 3;          // Estimated queue length in number of vehicles
  float density = 4;               // Vehicle density (veh/km)
}
```

### 3. Control & Telemetry Commands
- **`ControlCommand`**: Transmits actions (`START = 1`, `PAUSE = 2`, `STOP = 3`, `RESET = 4`).
- **`SystemState`**: Returns downstream status (`active`, `state`, `server_time`).

---

## 🛠️ Compiling Protobuf Definitions

To recompile the Python gRPC stubs from `synapse_hft.proto`:

```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Execute grpc_tools compiler from repository root
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    proto/synapse_hft.proto
```

This updates:
- `proto/synapse_hft_pb2.py` (Message serializations and descriptor classes)
- `proto/synapse_hft_pb2_grpc.py` (gRPC Stub and Servicer base classes)

---

## 🚀 Performance & Network Tuning

1. **Max Message Size**: gRPC channels in `src/infrastructure/grpc_connector.py` are initialized with:
   ```python
   options = [
       ('grpc.max_send_message_length', 50 * 1024 * 1024),    # 50 MB Send Limit
       ('grpc.max_receive_message_length', 50 * 1024 * 1024), # 50 MB Receive Limit
       ('grpc.keepalive_time_ms', 10000),                     # 10s Keepalive Ping
       ('grpc.keepalive_timeout_ms', 5000),                   # 5s Timeout
       ('grpc.http2.max_pings_without_data', 0),              # Continuous Keepalive
   ]
   ```
2. **Auto-Recovery**: If the downstream controller restarts, `src/infrastructure/hft_recovery.py` intercepts `grpc.RpcError`, re-establishes the HTTP/2 channel, and automatically re-invokes `LoadScenario` before re-opening `StreamTraffic`.

---

<p align="center">
  <sub>SYNAPSE HFT-Link — Noxfort Systems Transport Protocols</sub>
</p>
