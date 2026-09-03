// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// File: ui/src-tauri/src/backend/ipc.rs
// Author: Gabriel Moraes
// Date: 2026-08-31

use std::io::{BufRead, BufReader, Write};
use std::process::ChildStdout;
use tauri::{AppHandle, Emitter, State};
use super::state::PythonProcessState;

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct IpcCommandEnvelope {
    pub action: String,
    #[serde(default)]
    pub id: Option<String>,
    #[serde(default)]
    pub payload: serde_json::Value,
}

#[tauri::command]
pub fn send_synapse_command(
    state: State<'_, PythonProcessState>,
    action: String,
    payload: Option<serde_json::Value>,
    id: Option<String>,
) -> Result<(), String> {
    let mut stdin_guard = state.stdin.lock().map_err(|e| e.to_string())?;

    if let Some(ref mut stdin) = *stdin_guard {
        let envelope = IpcCommandEnvelope {
            action: action.clone(),
            id: id.clone(),
            payload: payload.unwrap_or(serde_json::json!({})),
        };

        let json_str = serde_json::to_string(&envelope).map_err(|e| e.to_string())?;
        writeln!(stdin, "{}", json_str).map_err(|e| e.to_string())?;
        stdin.flush().map_err(|e| e.to_string())?;
        if action != "ping" {
            eprintln!("[Tauri IPC] 📤 Comando despachado: action='{}' (id={:?})", action, id);
        }
        Ok(())
    } else {
        eprintln!("[Tauri IPC] ❌ Falha: Processo Python não está com STDIN conectado!");
        Err("Python backend process stdin is not available".to_string())
    }
}

pub fn spawn_stdout_listener(stdout: ChildStdout, app_handle: AppHandle) {
    std::thread::spawn(move || {
        let mut first_message = true;
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            if let Ok(line_str) = line {
                let trimmed = line_str.trim();
                if trimmed.is_empty() {
                    continue;
                }

                if first_message {
                    first_message = false;
                    eprintln!("[Tauri IPC] 🟢 CONECTADO: Canal STDOUT com Core Python estabelecido com sucesso.");
                }

                if let Ok(value) = serde_json::from_str::<serde_json::Value>(trimmed) {
                    if let Some(obj) = value.as_object() {
                        let msg_type = obj.get("type").and_then(|v| v.as_str());
                        if msg_type == Some("event") {
                            if let Some(event_name) = obj.get("event").and_then(|v| v.as_str()) {
                                let topic = format!("synapse:{}", event_name);
                                let data = obj.get("data").cloned().unwrap_or(serde_json::Value::Null);
                                let _ = app_handle.emit(&topic, data);
                            }
                        } else if msg_type == Some("response") {
                            let _ = app_handle.emit("synapse:response", &value);
                        }
                    }
                } else {
                    eprintln!("[Tauri IPC] ⚠️ Linha não-JSON do Python: {}", trimmed);
                }
            }
        }
        eprintln!("[Tauri IPC] 🔴 DESCONECTADO: Canal STDOUT com Core Python foi encerrado.");
    });
}
