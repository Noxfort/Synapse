# 02. UI Architecture & Modern Frontend (Tauri v2 + React)

Located in the `ui/` directory, the SYNAPSE frontend is a high-performance **Tauri v2 + React 18 + TypeScript + Tailwind CSS** desktop application.

It communicates with the heavy, multi-threaded PyTorch backend via **Zero-Network-Port Piped STDIO IPC**, guaranteeing that zero TCP/HTTP ports are opened on the host system.

---

## 1. Structure & Layout Components

The frontend is structured in `ui/src/`:
- **`Header`** (`ui/src/components/layout/Header.tsx`): Manages top navigation, real-time operating phase indicators, IPC pipe heartbeat, and dynamic PT-BR / EN-US language switching.
- **`Sidebar`** (`ui/src/components/layout/Sidebar.tsx`): Controls the state machine lifecycle (Optimization, Offline Bootstrap, Online HFT-Link Operation) and lists active data sources with Local/Global origin toggling.
- **`SumoMapCanvas`** (`ui/src/components/map/SumoMapCanvas.tsx`): Hardware-accelerated 2D Canvas/WebGL road network visualizer supporting smooth pan, zoom, traffic light highlights, and real-time speed heatmaps.
- **`LiveDashboard`** (`ui/src/components/dashboard/LiveDashboard.tsx`): Real-time telemetry powered by **Apache ECharts** (velocity, occupancy, and packet throughput at 60 FPS).
- **`XaiInspector`** (`ui/src/components/xai/XaiInspector.tsx`): Explainable AI & Safety Auditor panel displaying physical verification verdicts (`SAFE` vs `VETO`) and temporal attribution bars ($t-11$ to $t_0$).
- **`LogConsole`** (`ui/src/components/layout/LogConsole.tsx`): Retractable terminal dock for real-time system events with log-level filtering.

---

## 2. Zero-Port IPC Bridge (`Piped STDIO`)

Communication between Tauri (Rust) and SYNAPSE Core (Python):
1. **Rust Sidecar**: Tauri spawns `python3 -m src.ipc.stdio_daemon` as a background child process.
2. **Streaming Events (Python $\rightarrow$ React)**: Domain signals emitted by `MainController` / `InferenceEngine` are serialized as newline-delimited JSON envelopes (`IpcEvent`) on `sys.stdout`. Rust streams them directly to React via `app_handle.emit("synapse:<event>", payload)`.
3. **User Commands (React $\rightarrow$ Python)**: React invokes `send_synapse_command(action, payload)`. Rust writes the JSON line to `sys.stdin` of the Python process.

---

## 3. Internationalization (i18n)

Localization is powered by `i18next` + `react-i18next` with structured JSON locale dictionaries:
- `ui/src/i18n/locales/pt_BR.json` (Portuguese - Brazil)
- `ui/src/i18n/locales/en_US.json` (English - US)

Language toggling is instantaneous without restarting the process.
