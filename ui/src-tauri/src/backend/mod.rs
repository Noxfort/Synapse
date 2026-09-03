// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// File: ui/src-tauri/src/backend/mod.rs
// Author: Gabriel Moraes
// Date: 2026-08-31

pub mod state;
pub mod ipc;

pub use state::PythonProcessState;
pub use ipc::send_synapse_command;

use std::path::PathBuf;
use std::process::{Command, Stdio};
use tauri::AppHandle;

pub fn find_project_root() -> PathBuf {
    if let Ok(root_env) = std::env::var("SYNAPSE_ROOT") {
        let p = PathBuf::from(root_env);
        if p.exists() {
            return p;
        }
    }

    let mut cur = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    for _ in 0..8 {
        if cur.join("synapse.py").exists() || cur.join("src/ipc/stdio_daemon.py").exists() {
            return cur;
        }
        if let Some(parent) = cur.parent() {
            cur = parent.to_path_buf();
        } else {
            break;
        }
    }

    if let Ok(exe) = std::env::current_exe() {
        let mut cur = exe;
        for _ in 0..8 {
            if cur.join("synapse.py").exists() || cur.join("src/ipc/stdio_daemon.py").exists() {
                return cur;
            }
            if let Some(parent) = cur.parent() {
                cur = parent.to_path_buf();
            } else {
                break;
            }
        }
    }

    let known_fallback = PathBuf::from("/home/gabriel-moraes/Documentos/SYNAPSE_CORE");
    if known_fallback.exists() {
        return known_fallback;
    }

    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

pub fn spawn_python_backend(app_handle: AppHandle, state: &PythonProcessState) {
    let root = find_project_root();
    let candidates = [
        root.join(".venv/bin/python3"),
        root.join(".venv/bin/python"),
        root.join(".venv/Scripts/python.exe"),
        PathBuf::from("/home/gabriel-moraes/Documentos/SYNAPSE_CORE/.venv/bin/python3"),
    ];

    let mut python_bin = "python3".to_string();
    for candidate in &candidates {
        if candidate.exists() {
            python_bin = candidate.to_string_lossy().to_string();
            break;
        }
    }

    eprintln!("[Tauri] 🚀 Invocando backend Python: '{}' no diretório '{:?}'", python_bin, root);

    let mut child = match Command::new(&python_bin)
        .args(["-m", "src.ipc.stdio_daemon"])
        .env("PYTHONUNBUFFERED", "1")
        .env("PYTHONPATH", &root)
        .env_remove("LD_LIBRARY_PATH")
        .env_remove("LD_PRELOAD")
        .current_dir(&root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
    {
        Ok(c) => {
            eprintln!("[Tauri] ✅ Processo Python iniciado com sucesso (PID: {})", c.id());
            c
        }
        Err(e) => {
            eprintln!("[Tauri] ❌ Falha ao iniciar processo Python ({}) em {:?}: {}", python_bin, root, e);
            return;
        }
    };

    if let Some(stdin) = child.stdin.take() {
        let mut stdin_guard = state.stdin.lock().unwrap();
        *stdin_guard = Some(stdin);
    }

    let stdout = child.stdout.take().expect("Failed to open child stdout");
    {
        let mut proc_guard = state.process.lock().unwrap();
        *proc_guard = Some(child);
    }

    ipc::spawn_stdout_listener(stdout, app_handle);
}

pub fn kill_backend(state: &PythonProcessState) {
    if let Ok(mut proc_guard) = state.process.lock() {
        if let Some(mut child) = proc_guard.take() {
            let _ = child.kill();
            eprintln!("[Tauri] 🛑 Backend Python finalizado com sucesso.");
        }
    }
}
