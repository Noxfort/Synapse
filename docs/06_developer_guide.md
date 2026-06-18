# 06. Developer Guide

This guide is intended for engineers actively contributing to the SYNAPSE codebase, particularly those modifying the HFT-Link or running the test suites.

## 1. Modifying the HFT-Link (Protobuf)

If you need to change the data structures sent to CARINA (e.g., adding a new traffic metric like `CO2_emissions` to the `TrafficFrame`), you must modify the `.proto` definitions and recompile the Python stubs.

1. **Locate the Proto File**: `proto/synapse_link.proto`.
2. **Make your changes**.
3. **Recompile**:
   From the root of the repository, run the `grpcio-tools` compiler:
   ```bash
   python -m grpc_tools.protoc -I./proto --python_out=./src/infrastructure/grpc --grpc_python_out=./src/infrastructure/grpc ./proto/synapse_link.proto
   ```
4. **Fix Imports**: The Google Protobuf compiler for Python has a known quirk where it generates absolute imports. You may need to manually open `synapse_link_pb2_grpc.py` and change `import synapse_link_pb2` to `from . import synapse_link_pb2`.

## 2. Running the Test Suite

We use `pytest` for all unit and integration tests.

- **Run all tests**:
  ```bash
  pytest tests/
  ```
- **Run specific Agent tests** (e.g., to verify your new PyTorch tensor operations):
  ```bash
  pytest tests/agents/test_fuser_agent.py
  ```
- **Coverage Report**:
  ```bash
  pytest --cov=src tests/
  ```

> [!WARNING]
> Do not mock the PyTorch tensors with native Python lists during tests. Always use `torch.randn()` to ensure `dtype` and `device` checks (CPU vs CUDA) behave realistically.
