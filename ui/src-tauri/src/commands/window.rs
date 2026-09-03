// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// File: ui/src-tauri/src/commands/window.rs
// Author: Gabriel Moraes
// Date: 2026-08-31

use tauri::WebviewWindow;

#[tauri::command]
pub fn toggle_fullscreen(window: WebviewWindow) -> Result<bool, String> {
    let is_fs = window.is_fullscreen().map_err(|e| e.to_string())?;
    let target = !is_fs;
    window.set_fullscreen(target).map_err(|e| e.to_string())?;
    Ok(target)
}

#[tauri::command]
pub fn minimize_to_tray(window: WebviewWindow) -> Result<(), String> {
    window.hide().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn restore_from_tray(window: WebviewWindow) -> Result<(), String> {
    window.show().map_err(|e| e.to_string())?;
    window.unminimize().map_err(|e| e.to_string())?;
    window.set_focus().map_err(|e| e.to_string())
}
