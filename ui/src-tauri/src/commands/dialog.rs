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
// File: ui/src-tauri/src/commands/dialog.rs
// Author: Gabriel Moraes
// Date: 2026-08-31

use std::fs;
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};

static IS_DIALOG_ACTIVE: AtomicBool = AtomicBool::new(false);

struct DialogGuard;

impl DialogGuard {
    fn try_acquire() -> Option<Self> {
        if IS_DIALOG_ACTIVE
            .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
            .is_ok()
        {
            Some(DialogGuard)
        } else {
            None
        }
    }
}

impl Drop for DialogGuard {
    fn drop(&mut self) {
        IS_DIALOG_ACTIVE.store(false, Ordering::SeqCst);
    }
}

#[tauri::command]
pub async fn pick_file_dialog(
    title: Option<String>,
    filter_name: Option<String>,
    filter_extensions: Option<Vec<String>>,
) -> Result<Option<String>, String> {
    let _guard = match DialogGuard::try_acquire() {
        Some(g) => g,
        None => {
            eprintln!("[Tauri] pick_file_dialog ignorado: um diálogo de arquivo já está ativo.");
            return Ok(None);
        }
    };

    tokio::task::spawn_blocking(move || {
        let mut cmd = Command::new("zenity");
        cmd.arg("--file-selection");
        cmd.arg("--modal");
        if let Some(ref t) = title {
            cmd.arg(format!("--title={}", t));
        }
        if let (Some(ref name), Some(ref exts)) = (filter_name, filter_extensions) {
            let patterns = exts
                .iter()
                .map(|e| format!("*.{}", e.trim_start_matches('.')))
                .collect::<Vec<_>>()
                .join(" ");
            cmd.arg(format!("--file-filter={} | {}", name, patterns));
        }
        match cmd.output() {
            Ok(output) => {
                if output.status.success() {
                    let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
                    if !path.is_empty() {
                        return Ok(Some(path));
                    }
                }
                Ok(None)
            }
            Err(e) => {
                eprintln!("[Tauri] Zenity open file error: {}", e);
                Err(e.to_string())
            }
        }
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn save_file_dialog(
    default_filename: Option<String>,
    title: Option<String>,
    filter_name: Option<String>,
    filter_extensions: Option<Vec<String>>,
) -> Result<Option<String>, String> {
    let _guard = match DialogGuard::try_acquire() {
        Some(g) => g,
        None => {
            eprintln!("[Tauri] save_file_dialog ignorado: um diálogo de arquivo já está ativo.");
            return Ok(None);
        }
    };
    tokio::task::spawn_blocking(move || {
        let mut cmd = Command::new("zenity");
        cmd.arg("--file-selection");
        cmd.arg("--save");
        cmd.arg("--confirm-overwrite");
        cmd.arg("--modal");

        if let Some(ref t) = title {
            cmd.arg(format!("--title={}", t));
        }
        if let Some(ref f) = default_filename {
            cmd.arg(format!("--filename={}", f));
        }
        let target_ext = filter_extensions
            .as_ref()
            .and_then(|exts| exts.first().map(|s| s.trim_start_matches('.').to_string()))
            .or_else(|| {
                default_filename.as_ref().and_then(|f| {
                    if let Some(pos) = f.rfind('.') {
                        Some(f[pos + 1..].to_string())
                    } else {
                        None
                    }
                })
            });

        if let (Some(ref name), Some(ref exts)) = (filter_name, filter_extensions) {
            let patterns = exts
                .iter()
                .map(|e| format!("*.{}", e.trim_start_matches('.')))
                .collect::<Vec<_>>()
                .join(" ");
            cmd.arg(format!("--file-filter={} | {}", name, patterns));
        }

        match cmd.output() {
            Ok(output) => {
                if output.status.success() {
                    let mut path = String::from_utf8_lossy(&output.stdout).trim().to_string();
                    if !path.is_empty() {
                        if let Some(ref ext) = target_ext {
                            let dot_ext = format!(".{}", ext.to_lowercase());
                            if !path.to_lowercase().ends_with(&dot_ext) {
                                path.push_str(&dot_ext);
                            }
                        }
                        return Ok(Some(path));
                    }
                }
                Ok(None)
            }
            Err(e) => {
                eprintln!("[Tauri] Zenity save file error: {}", e);
                Err(e.to_string())
            }
        }
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn write_file_bytes(file_path: String, base64_content: String) -> Result<(), String> {
    tokio::task::spawn_blocking(move || {
        use std::io::Write;
        // Decode base64 or raw string
        let clean_base64 = if let Some(idx) = base64_content.find(',') {
            &base64_content[idx + 1..]
        } else {
            &base64_content
        };

        // Standard base64 decode without extra crate dependencies
        match decode_base64_custom(clean_base64) {
            Ok(bytes) => {
                let mut file = fs::File::create(&file_path).map_err(|e| e.to_string())?;
                file.write_all(&bytes).map_err(|e| e.to_string())?;
                Ok(())
            }
            Err(e) => Err(format!("Base64 decoding error: {}", e)),
        }
    })
    .await
    .map_err(|e| e.to_string())?
}

fn decode_base64_custom(input: &str) -> Result<Vec<u8>, String> {
    let chars: Vec<char> = input.chars().filter(|c| !c.is_whitespace()).collect();
    let mut buffer: Vec<u8> = Vec::new();
    let mut i = 0;

    fn b64_val(c: char) -> Result<u32, String> {
        match c {
            'A'..='Z' => Ok(c as u32 - 'A' as u32),
            'a'..='z' => Ok(c as u32 - 'a' as u32 + 26),
            '0'..='9' => Ok(c as u32 - '0' as u32 + 52),
            '+' => Ok(62),
            '/' => Ok(63),
            '=' => Ok(0),
            _ => Err(format!("Invalid base64 character: {}", c)),
        }
    }

    while i < chars.len() {
        if i + 3 >= chars.len() {
            break;
        }
        let c1 = chars[i];
        let c2 = chars[i + 1];
        let c3 = chars[i + 2];
        let c4 = chars[i + 3];

        let n1 = b64_val(c1)?;
        let n2 = b64_val(c2)?;
        let n3 = b64_val(c3)?;
        let n4 = b64_val(c4)?;

        let triple = (n1 << 18) | (n2 << 12) | (n3 << 6) | n4;

        buffer.push(((triple >> 16) & 0xFF) as u8);
        if c3 != '=' {
            buffer.push(((triple >> 8) & 0xFF) as u8);
        }
        if c4 != '=' {
            buffer.push((triple & 0xFF) as u8);
        }

        i += 4;
    }

    Ok(buffer)
}
