# SYNAPSE Packaging & Distribution

> **Packaging, Containerization, and Production Deployment Pipeline**

---

## 📦 Overview

The `packaging/` directory contains tools and build scripts to produce standalone, self-contained distribution bundles for **SYNAPSE CORE**, including native Debian `.deb` packages, Docker images, and system service configurations.

---

## 🐧 Native Debian Package (`.deb`)

SYNAPSE can be compiled into a standalone Debian package that installs in `/opt/synapse` with automated desktop shortcuts and system path wrappers.

### 1. Build the Debian Package
Run the packaging script on an Ubuntu 22.04+ machine (or inside the build container):

```bash
# Execute package build script
bash packaging/build_deb.sh
```

### 2. Package File Structure
The generated package contains:
- `/opt/synapse/`: Compiled application binaries, PyTorch runtime, shared libraries, and assets.
- `/usr/bin/synapse`: Global execution wrapper script.
- `/usr/share/applications/synapse.desktop`: Linux desktop launcher menu entry.
- `/usr/share/icons/hicolor/128x128/apps/synapse.png`: Application branding icon.

### 3. Installing & Uninstalling the Package

```bash
# Install the .deb package
sudo dpkg -i synapse_1.0_amd64.deb

# Resolve any missing system dependencies if needed
sudo apt-get install -f

# Launch SYNAPSE globally
synapse

# Uninstall SYNAPSE
sudo apt remove synapse
```

---

## 🐳 Dockerized Build Environment

To ensure reproducible builds without contaminating the host operating system, build via Docker:

```bash
# Build the packaging image
docker build -t synapse-builder -f packaging/Dockerfile .

# Run the build inside container and output the .deb to host
docker run --rm -v $(pwd):/app -w /app synapse-builder bash packaging/build_deb.sh
```

---

## ⚙️ Headless Server Deployment (`systemd`)

For 24/7 edge computing nodes or municipal datacenter servers running in headless mode, configure a `systemd` service:

### 1. Create Service Unit (`/etc/systemd/system/synapse.service`)

```ini
[Unit]
Description=SYNAPSE Core Traffic Perception Daemon
After=network.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=synapse
Group=synapse
WorkingDirectory=/opt/synapse
Environment="SYNAPSE_ROOT=/opt/synapse"
Environment="SYNAPSE_HEADLESS=1"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/synapse --daemon
Restart=always
RestartSec=5s
LimitNOFILE=65536

# Sandboxing & Security
ProtectSystem=full
ProtectHome=read-only
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

### 2. Enable & Start Daemon

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service on boot
sudo systemctl enable synapse.service

# Start the service
sudo systemctl start synapse.service

# Inspect live logs
journalctl -u synapse.service -f
```

---

<p align="center">
  <sub>SYNAPSE Packaging — Noxfort Systems Release Engineering</sub>
</p>
