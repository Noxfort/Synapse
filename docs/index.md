# SYNAPSE Technical Documentation Library

Welcome to the **Total Dimension** Technical Documentation for SYNAPSE_CORE. This library is structured to provide an exhaustive, class-level, and mathematical breakdown of every subsystem in the repository.

## The Library

1. **[01. Domain Entities & Core Structures](01_domain_entities.md)**
   - Detailed mapping of `src/domain/entities.py`.
   - The Trust Score hierarchy and `SourceStatus` state machines.

2. **[02. UI Architecture & Frontend](02_ui_architecture.md)**
   - PyQt6 event loops and decoupled rendering.
   - Translation, Themes, and the Signal Routing matrix.

3. **[03. Neural Models & Math (MARKVART™)](03_neural_models.md)**
   - Low-level PyTorch implementations.
   - Equations and reasoning behind `iTransformer`, `GATv2 Lite`, and `VAE-TCN`.

4. **[04. Execution Phases (ADAGIO™)](04_execution_phases.md)**
   - The thread execution model of Phase 0, Phase 1, and Phase 2.
   - Security constraints (Ghost-file protection and Master Locks).

5. **[05. Data Ingestion & HFT Network](05_data_ingestion_and_hft.md)**
   - The I/O boundary.
   - High-Frequency Transport (gRPC) and the Auto-Recovery self-healing loops.

6. **[06. Developer Guide](06_developer_guide.md)**
   - Compiling HFT-Link Protobufs.
   - Running the PyTest Suite.

7. **[07. Production Deployment Guide](07_deployment_guide.md)**
   - Running SYNAPSE securely in Headless mode.
   - Setting up `systemd` daemons and log rotation.

*Note: For the high-level macro vision, read the root `README.md` and `ARCHITECTURE.md` first.*
