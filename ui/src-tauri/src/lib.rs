// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// File: ui/src-tauri/src/lib.rs
// Author: Gabriel Moraes
// Date: 2026-08-31

pub mod backend;
pub mod commands;
pub mod tray;

use backend::ipc::send_synapse_command;
use backend::{spawn_python_backend, PythonProcessState};
use commands::dialog::{pick_file_dialog, save_file_dialog, write_file_bytes};
use commands::window::{minimize_to_tray, restore_from_tray, toggle_fullscreen};
use tauri::{Manager, WindowEvent};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let proc_state = PythonProcessState::new();

    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .manage(proc_state)
        .setup(|app| {
            let handle = app.handle().clone();
            let state = app.state::<PythonProcessState>();
            spawn_python_backend(handle, &state);
            tray::setup_tray(app)?;
            Ok(())
        })
        .on_window_event(|window, event| match event {
            WindowEvent::CloseRequested { api, .. } => {
                api.prevent_close();
                let _ = window.hide();
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![
            send_synapse_command,
            pick_file_dialog,
            save_file_dialog,
            write_file_bytes,
            toggle_fullscreen,
            minimize_to_tray,
            restore_from_tray
        ])
        .run(tauri::generate_context!())
        .expect("Error while running Tauri application");
}
