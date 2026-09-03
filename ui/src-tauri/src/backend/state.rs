// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// File: ui/src-tauri/src/backend/state.rs
// Author: Gabriel Moraes
// Date: 2026-08-31

use std::process::{Child, ChildStdin};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct PythonProcessState {
    pub stdin: Arc<Mutex<Option<ChildStdin>>>,
    pub process: Arc<Mutex<Option<Child>>>,
}

impl PythonProcessState {
    pub fn new() -> Self {
        Self {
            stdin: Arc::new(Mutex::new(None)),
            process: Arc::new(Mutex::new(None)),
        }
    }
}

impl Default for PythonProcessState {
    fn default() -> Self {
        Self::new()
    }
}
