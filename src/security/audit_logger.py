# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: src/security/audit_logger.py
# Author: Gabriel Moraes
# Date: 2026-09-03

"""
Security Audit Logger.
Persists structured security events (logins, configuration changes, user additions/deletions, lockdowns).
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.security.security_manager import get_user_config_dir
from src.utils.logging_setup import get_logger


class AuditLogger:
    """
    Registers audit actions (who, when, what) in a persistent JSON ledger.
    """

    def __init__(self, config_dir: Optional[str] = None, db_engine: Optional[Any] = None):
        self.logger = get_logger("AuditLogger")
        target_dir = config_dir or get_user_config_dir()
        self.audit_file = os.path.join(target_dir, "audit_log.json")
        self.db_engine = db_engine
        self._ensure_file()

    def _ensure_file(self) -> None:
        os.makedirs(os.path.dirname(self.audit_file), exist_ok=True)
        if not os.path.exists(self.audit_file):
            self._save_data([])

    def _load_data(self) -> List[Dict[str, Any]]:
        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading audit log: {e}")
            return []

    def _save_data(self, data: List[Dict[str, Any]]) -> None:
        try:
            with open(self.audit_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving audit log: {e}")

    def log_action(self, username: str, action: str, details: str = "") -> None:
        """Records an action in the audit log (both local JSON and central Database)."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "username": username or "UNKNOWN",
            "action": action,
            "details": details,
        }
        # 1. Local JSON persistence (guaranteed resilient fallback)
        data = self._load_data()
        data.append(entry)
        if len(data) > 1000:
            data = data[-1000:]
        self._save_data(data)

        # 2. Central Database persistence (PostgreSQL)
        if self.db_engine:
            try:
                conn = self.db_engine.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO security_audit_logs (created_at, username, action, details) VALUES (%s, %s, %s, %s)",
                        (entry["timestamp"], entry["username"], entry["action"], entry["details"])
                    )
                    conn.commit()
            except Exception as dbe:
                self.logger.debug(f"[DB AUDIT] Database record skipped (offline or uninitialized): {dbe}")

        self.logger.info(f"[AUDIT] User '{username}' executed '{action}'. Details: {details}")

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns the most recent logs first, preferring DB and falling back to JSON."""
        if self.db_engine:
            try:
                conn = self.db_engine.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT created_at, username, action, details FROM security_audit_logs ORDER BY created_at DESC LIMIT %s",
                        (limit,)
                    )
                    rows = cursor.fetchall()
                    if rows:
                        return [
                            {
                                "timestamp": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
                                "username": r[1],
                                "action": r[2],
                                "details": r[3] or "",
                            }
                            for r in rows
                        ]
            except Exception as dbe:
                self.logger.debug(f"[DB AUDIT] Database fetch fallback to JSON: {dbe}")

        data = self._load_data()
        return list(reversed(data))[:limit]

