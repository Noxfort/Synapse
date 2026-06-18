# 07. Production Deployment Guide

Running `python synapse.py` is sufficient for local development and UI inspection, but **unacceptable for production traffic control**. 

In a production environment, SYNAPSE must run as a headless, auto-restarting background daemon to ensure traffic lights never lose their connection to the intelligent perception grid.

## 1. Environment Preparation (Ubuntu 22.04 LTS)

1. Ensure the NVIDIA Drivers and CUDA Toolkit are installed at the system level.
2. Clone the repository into a secure location (e.g., `/opt/noxfort/synapse`).
3. Create the virtual environment and install the dependencies.
4. Download the `Model Vault` as specified in the README.

## 2. Running as a `systemd` Service

We strongly recommend `systemd` over Docker for SYNAPSE. Why? Because Docker containerization adds a layer of abstraction over the GPU and network host that can introduce microsecond latency jitter to the HFT-Link, and complicates raw UDP ingestion from inductive loops.

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/synapse-core.service
   ```

2. Add the following configuration (adjust paths for your user):
   ```ini
   [Unit]
   Description=SYNAPSE Core Perception Gateway
   After=network.target

   [Service]
   User=trafficadmin
   Group=trafficadmin
   WorkingDirectory=/opt/noxfort/synapse
   Environment="PATH=/opt/noxfort/synapse/.venv/bin"
   # Force Headless Mode for PyQt6
   Environment="QT_QPA_PLATFORM=offscreen"
   ExecStart=/opt/noxfort/synapse/.venv/bin/python synapse.py --headless

   # Auto-Restart Logic
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and Start the Service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable synapse-core
   sudo systemctl start synapse-core
   ```

## 3. Log Rotation

SYNAPSE logs heavily. Left unchecked, the `logs/` directory will consume the entire disk.

Create a `logrotate` rule:
```bash
sudo nano /etc/logrotate.d/synapse
```
```text
/opt/noxfort/synapse/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 trafficadmin trafficadmin
}
```
This keeps 14 days of history (for the `JuristAgent` audits) and compresses older logs.
