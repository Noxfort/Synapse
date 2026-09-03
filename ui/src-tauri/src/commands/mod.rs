// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// File: ui/src-tauri/src/commands/mod.rs
// Author: Gabriel Moraes
// Date: 2026-08-31

pub mod window;
pub mod dialog;

pub use window::{toggle_fullscreen, minimize_to_tray, restore_from_tray};
pub use dialog::pick_file_dialog;
