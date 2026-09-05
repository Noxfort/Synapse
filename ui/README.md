# SYNAPSE Desktop UI — Modern Desktop Frontend

> **High-Performance Desktop Client built with Tauri v2, React 18, TypeScript, Zustand, and Tailwind CSS**

---

## 🖥️ Overview

The **SYNAPSE UI** is an enterprise-grade desktop application engineered for municipal traffic control rooms and Smart City operators. It provides a real-time, hardware-accelerated dashboard to inspect the urban road topology, monitor the 11 MARKVART™ neural models, audit XAI decisions, and manage heterogeneous sensor ingestion feeds.

---

## ⚡ Key Technologies

- **Runtime Framework**: [Tauri v2](https://v2.tauri.app/) (Rust-backed lightweight native webview wrapper)
- **Frontend Core**: [React 18](https://react.dev/) + [TypeScript 5](https://www.typescriptlang.org/)
- **Build Tool**: [Vite 5](https://vitejs.dev/)
- **State Management**: [Zustand 4](https://github.com/pmndrs/zustand)
- **Styling**: [Tailwind CSS 3](https://tailwindcss.com/) + PostCSS + Custom Themes
- **Telemetry Visualizations**: [Apache ECharts 5](https://echarts.apache.org/) + `echarts-for-react`
- **Typography & Icons**: [Lucide React](https://lucide.dev/) + [KaTeX](https://katex.org/) (for mathematical formula rendering)
- **Internationalization**: [i18next](https://www.i18next.com/) (English, Portuguese, Spanish, French, Chinese, Russian)
- **IPC Transport**: Zero-Network-Port JSON-RPC over Standard I/O (`stdin`/`stdout`)

---

## 🏗️ Desktop Architecture & IPC Bridge

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TAURI v2 DESKTOP HOST                           │
│                                                                        │
│   ┌──────────────────────────────────────────────────────────────┐     │
│   │                      REACT 18 WEBVIEW                        │     │
│   │  - Zustand Reactive Stores (Sensors, System, Topology, XAI)  │     │
│   │  - ECharts Telemetry & Interactive Map Canvas                │     │
│   │  - KaTeX Mathematical Proofs & Jurist Reports                │     │
│   └──────────────────────────────┬───────────────────────────────┘     │
│                                  │ Tauri Invoke / Events               │
│   ┌──────────────────────────────▼───────────────────────────────┐     │
│   │                      RUST CORE (src-tauri)                   │     │
│   │  - Process Manager & Sidecar Lifecycle                       │     │
│   │  - System Tray Integration & Window Constraints              │     │
│   │  - Stdio Pipe Interceptor (Zero Network Ports)               │     │
│   └──────────────────────────────┬───────────────────────────────┘     │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │ STDIN / STDOUT (JSON-RPC)
┌──────────────────────────────────▼─────────────────────────────────────┐
│                       PYTHON BACKEND (StdioDaemon)                     │
│  - SignalBridge, CommandRouter, AppState, PyTorch Inference Loop       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Frontend Directory Structure

```text
ui/
├── index.html                 # HTML Entry point
├── package.json               # NPM dependency definitions & scripts
├── postcss.config.js          # PostCSS configuration
├── tailwind.config.js         # Tailwind CSS styling configuration
├── tsconfig.json              # TypeScript compilation rules
├── vite.config.ts             # Vite build configuration
├── src-tauri/                 # Rust Native Backend
│   ├── Cargo.toml             # Rust package configuration
│   ├── tauri.conf.json        # Tauri v2 application window & security capabilities
│   └── src/
│       ├── backend/           # Sidecar process manager & Stdio pipes
│       ├── commands/          # Rust Tauri commands exposed to React
│       ├── tray/              # System tray integration
│       ├── lib.rs             # Application setup and event bindings
│       └── main.rs            # Desktop native binary entrypoint
└── src_ui/                    # React 18 Source Code
    ├── App.tsx                # Main App component & router
    ├── main.tsx               # DOM bootstrap
    ├── index.css              # Global styles & Tailwind directives
    ├── components/            # Modular UI Components
    │   ├── common/            # Reusable buttons, badges, modals, loaders
    │   ├── dashboard/         # Real-time metric cards, speed/density charts
    │   ├── layout/            # Sidebar, Header, Status bar, Dock panels
    │   ├── map/               # Interactive road network topology & heatmap canvas
    │   ├── settings/          # Municipal parameters, language & theme config
    │   ├── wizard/            # Scenario configuration & sensor import wizard
    │   └── xai/               # Jurist explanation modal & audit report viewer
    ├── hooks/                 # Custom React hooks (telemetry, window resize)
    ├── i18n/                  # Multi-language translation dictionaries
    ├── services/              # Tauri IPC bridge client & RPC command wrappers
    ├── stores/                # Zustand Reactive State Stores
    │   ├── useBridgeManager.ts        # IPC transport coordinator & event listener
    │   ├── useSensorsStore.ts         # Sensor catalog, live values, trust scores
    │   ├── useSystemStore.ts          # System lifecycle, cycle latency, CPU/VRAM
    │   ├── useTopologyStore.ts        # SUMO road network nodes, edges & traffic lights
    │   ├── useXaiStore.ts             # Jurist explanations & anomaly alerts
    │   ├── useReportStore.ts          # Exportable audit reports & PDF generation
    │   ├── useEtlStore.ts             # Data ingestion wizard state
    │   └── useMunicipalSettingsStore.ts # City speed limits & thresholds
    ├── theme/                 # Dark/Light theme definitions
    ├── types/                 # TypeScript interfaces & domain contracts
    └── utils/                 # Formatting, mathematical helpers, geometry tools
```

---

## 🗄️ State Management (Zustand Stores)

1. **`useBridgeManager`**:
   - Manages the non-blocking IPC connection to the Python backend.
   - Listens to asynchronous backend events: `telemetry_tick`, `sensor_status_change`, `anomaly_detected`, `xai_report_generated`.
   - Dispatches structured JSON-RPC commands (`start_system`, `pause_system`, `add_sensor`, `load_map`).

2. **`useSensorsStore`**:
   - Maintains the live state machine for all connected data sources (`QUARANTINE`, `VALIDATING`, `ACTIVE`, `FALLBACK`, `PROBATION`, `REJECTED`).
   - Tracks live velocity, flow, confidence scores, and historical time-series buffers.

3. **`useTopologyStore`**:
   - Stores the active SUMO `.net.xml` road geometry, intersections (`MapNode`), and road edges (`MapEdge`).
   - Powers the interactive canvas rendering engine.

4. **`useXaiStore`**:
   - Holds legal explanations produced by the Qwen3 Jurist agent.
   - Renders KaTeX mathematical formulas explaining why a specific traffic phase was prioritized.

---

## 🛠️ Development & Building

### Prerequisites
- **Node.js**: v18.0.0 or higher (`npm` v9+)
- **Rust & Cargo**: Stable toolchain (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- **System Libraries (Linux / Ubuntu)**:
  ```bash
  sudo apt update
  sudo apt install -y libwebkit2gtk-4.1-dev build-essential curl wget file libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
  ```

---

### Scripts & Commands

```bash
# Navigate to ui directory
cd ui

# 1. Install Dependencies
npm install

# 2. Start Vite Frontend Development Server (Browser Only)
npm run dev

# 3. Start Native Tauri Desktop App (Live Hot-Reload with Rust Backend)
npm run tauri dev

# 4. Type-Check and Build Production Web Bundle
npm run build

# 5. Compile Native Desktop Release Binary (.deb, AppImage, Binary)
npm run tauri build
```

---

## 🌐 Localization (i18n)

The interface supports 6 municipal operational languages located in `src_ui/i18n/locales/`:
- 🇬🇧 English (`en`)
- 🇧🇷 Portuguese (`pt_BR`)
- 🇪🇸 Spanish (`es`)
- 🇫🇷 French (`fr`)
- 🇨🇳 Chinese (`zh`)
- 🇷🇺 Russian (`ru`)

Users can switch languages on-the-fly via the Settings view without reloading the application.

---

<p align="center">
  <sub>SYNAPSE Desktop UI — Noxfort Systems Frontend Engineering</sub>
</p>
