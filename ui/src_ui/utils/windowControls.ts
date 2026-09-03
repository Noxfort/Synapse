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
// File: ui/src_ui/utils/windowControls.ts
// Author: Gabriel Moraes
// Date: 2026-08-31

export async function toggleFullscreen(): Promise<boolean> {
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    const isFs = await invoke<boolean>('toggle_fullscreen');
    return isFs;
  } catch {
    // Fallback for standard web browser preview
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen().catch(() => {});
      return true;
    } else {
      await document.exitFullscreen().catch(() => {});
      return false;
    }
  }
}

export async function minimizeToTray(): Promise<void> {
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('minimize_to_tray');
  } catch (err) {
    console.warn('[WindowControls] Minimize to tray unavailable in browser mode:', err);
  }
}

export async function restoreFromTray(): Promise<void> {
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('restore_from_tray');
  } catch (err) {
    console.warn('[WindowControls] Restore from tray unavailable in browser mode:', err);
  }
}
